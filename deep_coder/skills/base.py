"""Skill base class and execution context."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from deep_coder.agent.orchestrator import Orchestrator
    from deep_coder.client import DeepSeekClient
    from deep_coder.config import Config
    from deep_coder.display import StatusPanel


@dataclass
class SkillContext:
    """Runtime context passed to every skill execution."""

    orchestrator: Orchestrator
    client: DeepSeekClient
    config: Config
    status_panel: Optional[StatusPanel]
    cwd: str


class Skill(ABC):
    """Base class for developer skills (slash commands backed by AI)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name including slash, e.g. '/review'."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description for /help."""
        ...

    @property
    @abstractmethod
    def usage(self) -> str:
        """Usage string, e.g. '/review [file|staged]'."""
        ...

    @abstractmethod
    async def execute(self, arg: str, ctx: SkillContext) -> None:
        """Run the skill. Output is printed directly to console."""
        ...

    async def _run_git(self, *args: str, cwd: str | None = None) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def _run_shell(self, cmd: str, cwd: str | None = None, timeout: int = 120) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return 1, "", f"Command timed out after {timeout}s"
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def _stream_to_console(self, ctx: SkillContext, prompt: str, use_tools: bool = False) -> str:
        """Send a prompt through the orchestrator and stream the response."""
        from deep_coder.display import StreamPrinter, print_response

        printer = StreamPrinter(status_panel=ctx.status_panel)

        if use_tools:
            result = await ctx.orchestrator.process(
                prompt,
                on_token=printer.on_token,
            )
        else:
            from deep_coder.models import ModelRole
            response = await ctx.client.collect_stream(
                messages=[
                    {"role": "system", "content": "You are Deep Coder, an expert software engineer."},
                    {"role": "user", "content": prompt},
                ],
                model_role=ModelRole.PRO,
                on_token=printer.on_token,
            )
            result = response.get("content") or ""

        printer.finish()
        if ctx.status_panel:
            ctx.status_panel.refresh(force=True)

        if not printer.get_content():
            print_response(result)

        return result
