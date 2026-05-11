"""Rich console output for Deep Coder — streaming, spinners, tool call visualization."""

from __future__ import annotations

import asyncio
import shutil
import sys
import time
from typing import TYPE_CHECKING, Any, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    from deep_coder.client import UsageStats

THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "tool": "magenta",
    "model.pro": "bold blue",
    "model.flash": "bold green",
    "dim": "dim white",
})

console = Console(theme=THEME)


def print_banner() -> None:
    banner = Text()
    banner.append("Deep Coder", style="bold cyan")
    banner.append(" v0.1.0", style="dim")
    banner.append(" — powered by DeepSeek V4\n", style="dim")
    banner.append("  Pro  ", style="model.pro")
    banner.append("for planning & verification  ", style="dim")
    banner.append("Flash ", style="model.flash")
    banner.append("for parallel execution\n", style="dim")
    banner.append("  Type ", style="dim")
    banner.append("/help", style="bold")
    banner.append(" for commands, ", style="dim")
    banner.append("/exit", style="bold")
    banner.append(" to quit", style="dim")
    console.print(Panel(banner, border_style="cyan", padding=(0, 1)))


def print_error(message: str) -> None:
    console.print(f"[error]Error:[/error] {message}")


def print_warning(message: str) -> None:
    console.print(f"[warning]Warning:[/warning] {message}")


def print_info(message: str) -> None:
    console.print(f"[info]{message}[/info]")


def print_success(message: str) -> None:
    console.print(f"[success]{message}[/success]")


def print_tool_call(tool_name: str, status: str = "calling") -> None:
    icon = {"calling": "->", "completed": "OK", "failed": "XX"}.get(status, "->")
    style = {"calling": "tool", "completed": "success", "failed": "error"}.get(status, "tool")
    console.print(f"  [{style}][{icon}][/{style}] {tool_name}", highlight=False)


def print_task_status(task_id: str | None, status: str) -> None:
    if status.startswith("tool:"):
        tool_name = status.split(":", 1)[1]
        prefix = f"  [{task_id}] " if task_id else "  "
        console.print(f"{prefix}[tool]{tool_name}[/tool]", highlight=False)
    elif status.startswith("plan:"):
        count = status.split(":", 1)[1]
        console.print(f"  [info]Plan created: {count}[/info]")
    elif status == "running":
        if task_id:
            console.print(f"  [dim]Worker started: {task_id}[/dim]")
    elif status == "completed":
        if task_id:
            console.print(f"  [success]Worker completed: {task_id}[/success]")
    elif status.startswith("failed"):
        msg = status.split(":", 1)[1] if ":" in status else ""
        if task_id:
            console.print(f"  [error]Worker failed: {task_id} — {msg}[/error]")


def print_response(content: str) -> None:
    console.print()
    console.print(Markdown(content))
    console.print()


def print_help() -> None:
    print_help_extended()


def print_help_extended() -> None:
    help_text = """
**Skills:**
- `/review [file|staged]` — AI code review for staged changes or a file
- `/commit [hint]`   — Generate smart commit message and commit
- `/test [command]`   — Run tests (auto-detect) and analyze failures
- `/fix <error>`      — Analyze error message and fix root cause
- `/think <question>` — Deep reasoning for architecture/design questions
- `/pr [base]`        — Generate PR title and description from branch diff
- `/explain [file:lines]` — Explain code, file, or project overview

**Session:**
- `/clear`     — Clear conversation history and file snapshots
- `/compact`   — Compress conversation history to free context space
- `/cost`      — Show token usage and estimated cost
- `/save [name]` — Save current session for later
- `/resume [name]` — Resume a saved session (no arg = list sessions)

**Code:**
- `/diff`      — Show all file changes made in this session
- `/undo`      — Revert the last file modification
- `/init`      — Scan project and generate CODER.md

**Settings:**
- `/config`    — Show current configuration
- `/model`     — Show model information
- `/vim`       — Toggle vi input mode

**General:**
- `/help`      — Show this help message
- `/exit`      — Exit Deep Coder

**Tips:**
- Multi-line input: press Escape then Enter
- Interrupt generation: Ctrl+C
"""
    console.print(Markdown(help_text))


class StreamPrinter:
    """Accumulates streaming tokens and prints them."""

    def __init__(self, status_panel: StatusPanel | None = None) -> None:
        self._buffer: list[str] = []
        self._started = False
        self._status_panel = status_panel

    async def on_token(self, token: str) -> None:
        if not self._started:
            console.print()
            self._started = True
        console.print(token, end="", highlight=False)
        self._buffer.append(token)
        if self._status_panel:
            self._status_panel.refresh()

    def get_content(self) -> str:
        return "".join(self._buffer)

    def finish(self) -> None:
        if self._started:
            console.print()


class StatusPanel:
    """Floating top-right panel showing real-time token usage and cost."""

    PANEL_WIDTH = 26
    PANEL_HEIGHT = 5
    THROTTLE_INTERVAL = 1.0

    def __init__(self, usage: UsageStats) -> None:
        self._usage = usage
        self._last_render: float = 0.0

    def refresh(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_render) < self.THROTTLE_INTERVAL:
            return
        self._last_render = now
        self._render()

    def _render(self) -> None:
        cols, _ = shutil.get_terminal_size((80, 24))
        if cols < self.PANEL_WIDTH + 4:
            return

        u = self._usage
        pro_tokens = u.pro_prompt_tokens + u.pro_completion_tokens
        flash_tokens = u.flash_prompt_tokens + u.flash_completion_tokens
        total_tokens = pro_tokens + flash_tokens
        pro_cost = u.estimated_cost("deepseek-v4-pro", u.pro_prompt_tokens, u.pro_completion_tokens)
        flash_cost = u.estimated_cost("deepseek-v4-flash", u.flash_prompt_tokens, u.flash_completion_tokens)
        total_cost = pro_cost + flash_cost

        w = self.PANEL_WIDTH
        inner = w - 2
        col_start = cols - w

        lines = [
            "┌─ Cost " + "─" * (inner - 7) + "┐",
            f"│ {'Pro':6s} {pro_tokens:>7,}  ${pro_cost:>.3f} │",
            f"│ {'Flash':6s} {flash_tokens:>7,}  ${flash_cost:>.3f} │",
            f"│ {'Total':6s} {total_tokens:>7,}  ${total_cost:>.3f} │",
            "└" + "─" * inner + "┘",
        ]

        out = sys.stdout
        out.write("\0337")  # save cursor
        for i, line in enumerate(lines):
            out.write(f"\033[{i + 1};{col_start + 1}H{line}")
        out.write("\0338")  # restore cursor
        out.flush()
