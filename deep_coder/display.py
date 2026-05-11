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
    """Print a geek-style cyberpunk splash screen for Deep Coder."""
    from deep_coder import __version__
    import platform

    term_w, _ = shutil.get_terminal_size((80, 24))

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: BOOT SEQUENCE
    # ═══════════════════════════════════════════════════════════════════════════
    _boot_sequence(__version__, platform, term_w)

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: MAIN BANNER
    # ═══════════════════════════════════════════════════════════════════════════
    banner = Text()

    # ── ASCII art title ───────────────────────────────────────────────────────
    title = r"""
   ██████╗ ███████╗███████╗██████╗      ██████╗ ██████╗ ██████╗ ███████╗██████╗ 
   ██╔══██╗██╔════╝██╔════╝██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗
   ██║  ██║█████╗  █████╗  ██████╔╝    ██║     ██║   ██║██║  ██║█████╗  ██████╔╝
   ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝     ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗
   ██████╔╝███████╗███████╗██║         ╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║
   ╚═════╝ ╚══════╝╚══════╝╚═╝          ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
"""  # noqa: E501
    banner.append(title, style="bold bright_cyan")

    # ── Tagline ───────────────────────────────────────────────────────────────
    banner.append("  ── ", style="dim")
    banner.append("Powered by DeepSeek V4  ·  ", style="cyan")
    banner.append(f"v{__version__}", style="bold bright_cyan")
    banner.append("  ·  ", style="cyan")
    banner.append("[THE MOST COST-EFFECTIVE CODE ASSISTANT]", style="bold yellow")
    banner.append("  ──\n\n", style="dim")

    # ── Architecture diagram ──────────────────────────────────────────────────
    _append_arch_diagram(banner)

    # ── Quick reference ───────────────────────────────────────────────────────
    _append_quickref(banner)

    # ── Status line ───────────────────────────────────────────────────────────
    banner.append("  ", style="dim")
    banner.append("[0x7F3A_B001]", style="bold magenta")
    banner.append("  ·  ", style="dim")
    banner.append("STATUS: SYSTEM READY", style="bold green")
    banner.append("  ·  ", style="dim")
    banner.append("TYPE YOUR QUERY BELOW", style="bold cyan")
    banner.append("  ·  ", style="dim")
    banner.append("[ONLINE]", style="bold green")
    banner.append("\n")

    console.print(
        Panel(
            banner,
            border_style="bright_cyan",
            padding=(1, 3),
            title="[bold bright_cyan]◈ DEEP CODER ◈[/bold bright_cyan]",
            subtitle="[dim]boot sequence complete ✓[/dim]",
        )
    )


def _boot_sequence(__version__: str, platform, term_w: int) -> None:
    """Simulate a cyberpunk-style boot sequence."""
    import random

    BOOT_LINES = [
        ("[bright_cyan]╔══ BIOS v2.04.13 ═══════════════════════════════════════════╗[/]", 0.02),
        (f"[bright_cyan]║[/] [dim]MFR:[/] [bold green]DEEPSEEK INDUSTRIES[/]        [dim]SN:[/] [bold magenta]DS-{random.randint(9000,9999)}-{random.randint(1000,9999)}[/]  [bright_cyan]║[/]", 0.04),
        (f"[bright_cyan]║[/] [dim]CPU:[/] [bold blue]DeepSeek V4 Pro[/] @ 2.8PHz        [dim]CORES:[/] [bold cyan]8[/]         [bright_cyan]║[/]", 0.03),
        (f"[bright_cyan]║[/] [dim]MEM:[/] [bold green]128TB HBM4[/]  [dim]BUS:[/] 8192-bit    [dim]ECC:[/] [bold green]OK[/]        [bright_cyan]║[/]", 0.03),
        (f"[bright_cyan]║[/] [dim]SYS:[/] {platform.system():10s} {platform.machine():>8s}        [dim]VER:[/] [bold cyan]{__version__:<10s}[/] [bright_cyan]║[/]", 0.03),
        ("[bright_cyan]╚══ BIOS v2.04.13 ═══════════════════════════════════════════╝[/]", 0.02),
        ("", 0.05),
        ("[bold yellow]>>> INITIALIZING NEURAL SUBSYSTEMS...[/]", 0.06),
        ("  [dim]├─[/] [green]✓[/] Orchestrator Core [Pro V4]  [dim]...[/] [bold green]ONLINE[/]", 0.04),
        ("  [dim]├─[/] [green]✓[/] Worker Swarm [Flash V4]   [dim]...[/] [bold green]ONLINE[/]  [dim](max_workers=5)[/]", 0.04),
        ("  [dim]├─[/] [green]✓[/] Tool Registry             [dim]...[/] [bold green]LOADED[/] [dim](read/write/shell/search/git)[/]", 0.03),
        ("  [dim]├─[/] [green]✓[/] Skill Registry            [dim]...[/] [bold green]LOADED[/] [dim](review/commit/fix/think/explain/pr/test)[/]", 0.03),
        ("  [dim]├─[/] [green]✓[/] Prompt Templates          [dim]...[/] [bold green]COMPILED[/]", 0.03),
        ("  [dim]└─[/] [green]✓[/] Configuration             [dim]...[/] [bold green]PARSED[/]", 0.04),
        ("", 0.03),
        ("[bold yellow]>>> SECURE HANDSHAKE WITH API ENDPOINT...[/]", 0.05),
        ("  [dim]├─[/] [cyan]⟳[/] api.deepseek.com:443        [dim]...[/] [bold green]CONNECTED[/] [dim](TLS 1.3)[/]", 0.04),
        ("  [dim]└─[/] [cyan]⟳[/] Auth Token                   [dim]...[/] [bold green]VERIFIED[/]", 0.04),
        ("", 0.03),
        ("[bold yellow]>>> LOADING SYSTEM MODULES...[/]", 0.04),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.agent.orchestrator[/]      [0x0000_0100]", 0.02),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.agent.worker[/]            [0x0000_0200]", 0.02),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.tools.file_ops[/]          [0x0000_0300]", 0.02),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.tools.shell[/]             [0x0000_0400]", 0.02),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.tools.search[/]            [0x0000_0500]", 0.02),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.tools.git[/]               [0x0000_0600]", 0.02),
        (f"  [dim]├─[/] [green]✓[/] [dim]deep_coder.skills.base[/]             [0x0000_0700]", 0.02),
        (f"  [dim]└─[/] [green]✓[/] [dim]deep_coder.display[/]                 [0x0000_0800]", 0.02),
        ("", 0.04),
        ("[bold green]╔══ ALL SYSTEMS NOMINAL ═══════════════════════════════════╗[/]", 0.03),
        (f"[bold green]║[/]  [bold]Deep Coder v{__version__}[/] booted successfully.                  [bold green]║[/]", 0.03),
        ("[bold green]╚══════════════════════════════════════════════════════════╝[/]", 0.04),
        ("", 0.05),
    ]

    for line, delay in BOOT_LINES:
        console.print(line, highlight=False)
        if delay > 0.01:
            time.sleep(delay)


def _append_arch_diagram(banner: Text) -> None:
    """Append the architecture diagram to the banner."""
    banner.append("  ╭─ ", style="bright_cyan")
    banner.append("ARCHITECTURE", style="bold bright_yellow")
    banner.append(" ─", style="bright_cyan")
    banner.append("───────────────────────────────────────────────────────────────", style="dim")
    banner.append("─╮\n", style="bright_cyan")

    banner.append("  │  ", style="bright_cyan")
    banner.append("┌──────────┐", style="bold blue")
    banner.append("                      ┌──────────────────────────────┐", style="bold green")
    banner.append("  │\n", style="bright_cyan")

    banner.append("  │  ", style="bright_cyan")
    banner.append("│  Pro V4  │", style="bold blue")
    banner.append("  ──plan/delegate──▶  ", style="dim")
    banner.append("│  Flash V4 Workers (parallel)  │", style="bold green")
    banner.append("  │\n", style="bright_cyan")

    banner.append("  │  ", style="bright_cyan")
    banner.append("│Orchstrtr│", style="bold blue")
    banner.append("  ◀──verify/merge──  ", style="dim")
    banner.append("│  read · write · shell · search  │", style="bold green")
    banner.append("  │\n", style="bright_cyan")

    banner.append("  │  ", style="bright_cyan")
    banner.append("└──────────┘", style="bold blue")
    banner.append("                      └──────────────────────────────┘", style="bold green")
    banner.append("  │\n", style="bright_cyan")

    banner.append("  ╰", style="bright_cyan")
    banner.append("───────────────────────────────────────────────────────────────────────────────", style="dim")
    banner.append("─╯\n\n", style="bright_cyan")


def _append_quickref(banner: Text) -> None:
    """Append quick reference commands to the banner."""
    banner.append("  ╭─ ", style="bright_cyan")
    banner.append("QUICK REF", style="bold bright_yellow")
    banner.append(" ─", style="bright_cyan")
    banner.append("───────────────────────────────────────────────", style="dim")
    banner.append("─╮\n", style="bright_cyan")

    banner.append("  │  ", style="bright_cyan")
    banner.append("/help", style="bold white")
    banner.append(" → commands  ", style="dim")
    banner.append("│  ", style="dim")
    banner.append("/exit", style="bold white")
    banner.append(" → quit    ", style="dim")
    banner.append("│  ", style="dim")
    banner.append("/cost", style="bold white")
    banner.append(" → usage    ", style="dim")
    banner.append("│  ", style="dim")
    banner.append("/init", style="bold white")
    banner.append(" → CODER.md", style="dim")
    banner.append("  │\n", style="bright_cyan")

    banner.append("  │  ", style="bright_cyan")
    banner.append("/review", style="bold white")
    banner.append(" → AI CR  ", style="dim")
    banner.append("│  ", style="dim")
    banner.append("/commit", style="bold white")
    banner.append(" → message ", style="dim")
    banner.append("│  ", style="dim")
    banner.append("/fix", style="bold white")
    banner.append(" → analyze  ", style="dim")
    banner.append("│  ", style="dim")
    banner.append("/think", style="bold white")
    banner.append(" → reason", style="dim")
    banner.append("  │\n", style="bright_cyan")

    banner.append("  ╰", style="bright_cyan")
    banner.append("─────────────────────────────────────────────────────────────────────────────", style="dim")
    banner.append("─╯\n\n", style="bright_cyan")


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
