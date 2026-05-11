"""Shell command execution tool."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from deep_coder.tools.base import Tool, ToolResult


class ExecShellTool(Tool):
    @property
    def name(self) -> str:
        return "exec_shell"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command and return its stdout/stderr. "
            "Use for running tests, git commands, builds, etc. "
            "Commands run in the current working directory."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default: 120.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command. Default: current directory.",
                },
            },
            "required": ["command"],
        }

    @property
    def requires_approval(self) -> bool:
        return True

    async def execute(
        self,
        command: str,
        timeout: int = 120,
        cwd: str | None = None,
        **_: Any,
    ) -> ToolResult:
        work_dir = cwd or os.getcwd()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult.error(f"Command timed out after {timeout}s: {command}")

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output_parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace')}")

            output = "\n".join(output_parts) if output_parts else "(no output)"
            exit_code = proc.returncode or 0

            if exit_code != 0:
                return ToolResult(
                    content=f"Exit code: {exit_code}\n{output}",
                    success=False,
                    metadata={"exit_code": exit_code},
                )
            return ToolResult.ok(output, exit_code=exit_code)
        except Exception as e:
            return ToolResult.error(f"Failed to execute command: {e}")
