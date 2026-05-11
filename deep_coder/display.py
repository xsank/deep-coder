"""Rich console output for Deep Coder — streaming, spinners, tool call visualization."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

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
    help_text = """
**Commands:**
- `/help`    — Show this help message
- `/clear`   — Clear conversation history
- `/config`  — Show current configuration
- `/exit`    — Exit Deep Coder
- `/model`   — Show current model info

**Tips:**
- Multi-line input: press Alt+Enter or Escape then Enter
- Interrupt generation: Ctrl+C
"""
    console.print(Markdown(help_text))


class StreamPrinter:
    """Accumulates streaming tokens and prints them."""

    def __init__(self) -> None:
        self._buffer: list[str] = []
        self._started = False

    async def on_token(self, token: str) -> None:
        if not self._started:
            console.print()
            self._started = True
        console.print(token, end="", highlight=False)
        self._buffer.append(token)

    def get_content(self) -> str:
        return "".join(self._buffer)

    def finish(self) -> None:
        if self._started:
            console.print()
