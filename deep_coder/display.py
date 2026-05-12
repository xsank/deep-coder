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
    banner.append("  ")
    banner.append("READY", style="bold green")
    banner.append("  ·  ", style="dim")
    banner.append("type your query or /help for commands", style="dim")
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
    """Clean boot sequence — aligned status lines, no box borders."""
    import random

    sn = f"DS-{random.randint(9000, 9999)}-{random.randint(1000, 9999)}"

    BOOT_LINES = [
        ("", 0.02),
        ("[bold yellow]  Initializing...[/]", 0.06),
        ("", 0.02),
        (f"  [green]✓[/] Orchestrator Core   [dim]Pro V4[/]         [bold green]online[/]", 0.04),
        (f"  [green]✓[/] Worker Swarm        [dim]Flash V4 ×5[/]    [bold green]online[/]", 0.04),
        (f"  [green]✓[/] Tool Registry       [dim]7 tools[/]        [bold green]loaded[/]", 0.03),
        (f"  [green]✓[/] Skill Registry      [dim]7 skills[/]       [bold green]loaded[/]", 0.03),
        (f"  [green]✓[/] API Connection      [dim]deepseek.com[/]   [bold green]connected[/]", 0.04),
        ("", 0.03),
        (f"  [bold green]Ready.[/]  [dim]{platform.system()} {platform.machine()}  ·  {sn}[/]", 0.05),
        ("", 0.04),
    ]

    for line, delay in BOOT_LINES:
        console.print(line, highlight=False)
        if delay > 0.01:
            time.sleep(delay)


def _append_arch_diagram(banner: Text) -> None:
    """Append a single-line architecture flow to the banner."""
    banner.append("  ARCHITECTURE ", style="bold bright_yellow")
    banner.append("─" * 50, style="dim")
    banner.append("\n\n")

    banner.append("  ")
    banner.append("Pro V4", style="bold blue")
    banner.append(" ── plan ──▶ ", style="dim")
    banner.append("Flash V4 Workers", style="bold green")
    banner.append(" (parallel)", style="dim")
    banner.append(" ── verify ──▶ ", style="dim")
    banner.append("Pro V4", style="bold blue")
    banner.append(" Summary", style="dim")
    banner.append("\n\n")


def _append_quickref(banner: Text) -> None:
    """Append quick reference commands in a clean grid."""
    banner.append("  COMMANDS ", style="bold bright_yellow")
    banner.append("─" * 54, style="dim")
    banner.append("\n\n")

    rows = [
        [("/help", "commands"), ("/review", "AI review"), ("/commit", "commit msg"), ("/fix", "auto-fix")],
        [("/think", "reasoning"), ("/explain", "explain"), ("/pr", "PR desc"), ("/test", "run tests")],
    ]

    col_w = 19
    for row in rows:
        banner.append("  ")
        for cmd, desc in row:
            banner.append(cmd, style="bold white")
            desc_text = f" {desc}"
            banner.append(desc_text, style="dim")
            pad = col_w - len(cmd) - len(desc_text)
            if pad > 0:
                banner.append(" " * pad)
        banner.append("\n")
    banner.append("\n")


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


def _format_elapsed(seconds: float) -> str:
    """Format seconds as human-friendly time string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


_PHASE_STYLES: dict[str, tuple[str, str]] = {
    "planning": ("blue", "Pro"),
    "executing": ("yellow", "Flash"),
    "verifying": ("green", "Pro"),
}


def print_phase(phase: str, detail: str = "") -> None:
    """Print a compact phase indicator — like Claude Code's step markers."""
    color, model = _PHASE_STYLES.get(phase, ("cyan", ""))
    model_tag = f" [dim]({model})[/dim]" if model else ""
    suffix = f"  [dim]{detail}[/dim]" if detail else ""
    console.print(f"\n  [{color}]●[/{color}] [bold]{phase.upper()}[/bold]{model_tag}{suffix}")


class PhaseSpinner:
    """Animated phase indicator with cycling dots and elapsed time.

    Usage::

        async with PhaseSpinner("planning", "analyzing request"):
            await long_running_call()
    """

    def __init__(self, phase: str, detail: str = "") -> None:
        self._phase = phase
        self._detail = detail.rstrip(".")
        self._start = 0.0
        self._live: Live | None = None
        self._update_task: asyncio.Task[None] | None = None

    def _render(self, dots: str = "") -> Text:
        color, model = _PHASE_STYLES.get(self._phase, ("cyan", ""))
        elapsed = time.monotonic() - self._start
        t = _format_elapsed(elapsed)

        line = Text()
        line.append("\n  ")
        line.append("●", style=color)
        line.append(f" {self._phase.upper()}", style="bold")
        line.append(f" ({model})", style="dim")
        if self._detail:
            line.append(f"  {self._detail}", style="dim")
        if dots:
            line.append(dots, style="dim")
        line.append(f"  {t}", style="dim")
        return line

    async def _animation_loop(self) -> None:
        try:
            while True:
                elapsed = time.monotonic() - self._start
                n = int(elapsed / 0.5) % 3 + 1
                if self._live:
                    self._live.update(self._render("." * n))
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            pass

    async def __aenter__(self) -> PhaseSpinner:
        self._start = time.monotonic()
        self._live = Live(
            self._render("."),
            console=console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()
        self._update_task = asyncio.create_task(self._animation_loop())
        return self

    async def __aexit__(self, exc_type: Any, *args: Any) -> None:
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None
        elapsed = time.monotonic() - self._start
        t = _format_elapsed(elapsed)
        color, model = _PHASE_STYLES.get(self._phase, ("cyan", ""))
        detail_s = f"  [dim]{self._detail}[/dim]" if self._detail else ""
        interrupted = " [yellow]interrupted[/yellow]" if exc_type else ""
        console.print(
            f"\n  [{color}]●[/{color}] [bold]{self._phase.upper()}[/bold]"
            f" [dim]({model})[/dim]{detail_s}  [dim]{t}[/dim]{interrupted}"
        )


def print_plan_summary(plan_desc: str, tasks: list[dict[str, str]]) -> None:
    """Print a compact plan overview — one line per task, no box."""
    console.print(f"    [dim]{plan_desc}[/dim]")
    for i, t in enumerate(tasks):
        is_last = i == len(tasks) - 1
        branch = "└─" if is_last else "├─"
        deps = ""
        if t.get("deps"):
            deps = f" [dim](← {', '.join(t['deps'])})[/dim]"
        console.print(f"    [dim]{branch}[/dim] [cyan]{t['id']}[/cyan] {t['desc']}{deps}")


class TaskProgressDisplay:
    """Compact inline progress for parallel task execution with animated header."""

    REFRESH_PER_SECOND = 4

    def __init__(self, detail: str = "") -> None:
        self._task_states: dict[str, dict[str, str]] = {}
        self._live: Live | None = None
        self._lock = asyncio.Lock()
        self._detail = detail
        self._start_time = 0.0

    def _build_renderable(self) -> Text:
        elapsed = time.monotonic() - self._start_time
        n = int(elapsed / 0.5) % 3 + 1
        dots = "." * n
        t = _format_elapsed(elapsed)

        result = Text()
        result.append("  ")
        result.append("●", style="bold yellow")
        result.append(" EXECUTING", style="bold")
        result.append(" (Flash)", style="dim")
        if self._detail:
            result.append(f"  {self._detail}", style="dim")
        result.append(f"{dots:<3s}", style="dim")
        result.append(f"  {t}", style="dim")
        result.append("\n")

        for tid, state in self._task_states.items():
            status = state.get("status", "pending")
            detail = state.get("detail", "")

            if status == "running":
                icon = "⟳"
                icon_style = "bold yellow"
                info = detail or "running"
                info_style = "yellow"
            elif status == "completed":
                icon = "✓"
                icon_style = "bold green"
                info = "done"
                info_style = "green"
            elif status == "failed":
                icon = "✗"
                icon_style = "bold red"
                info = detail or "failed"
                info_style = "red"
            else:
                icon = "○"
                icon_style = "dim"
                info = "waiting"
                info_style = "dim"

            result.append("    ")
            result.append(icon, style=icon_style)
            result.append(f" {tid}", style="cyan")
            result.append(f"  {info}", style=info_style)
            result.append("\n")

        return result

    async def start(self, tasks: list[Any]) -> None:
        self._start_time = time.monotonic()
        for t in tasks:
            self._task_states[t.id] = {
                "status": "pending",
                "desc": t.description[:40],
                "detail": "",
            }
        self._live = Live(
            self._build_renderable(),
            console=console,
            refresh_per_second=self.REFRESH_PER_SECOND,
            transient=True,
        )
        self._live.start()

    async def update(self, task_id: str, status: str, detail: str = "") -> None:
        async with self._lock:
            if task_id in self._task_states:
                self._task_states[task_id]["status"] = status
                if detail:
                    self._task_states[task_id]["detail"] = detail
            if self._live:
                self._live.update(self._build_renderable())

    async def stop(self) -> None:
        elapsed = time.monotonic() - self._start_time
        t = _format_elapsed(elapsed)
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None
        detail_s = f"  [dim]{self._detail}[/dim]" if self._detail else ""
        console.print(
            f"\n  [yellow]●[/yellow] [bold]EXECUTING[/bold]"
            f" [dim](Flash)[/dim]{detail_s}  [dim]{t}[/dim]"
        )
        for tid, state in self._task_states.items():
            status = state.get("status", "pending")
            if status == "completed":
                console.print(f"    [green]✓[/green] [cyan]{tid}[/cyan]  [green]done[/green]")
            elif status == "failed":
                detail = state.get("detail", "")
                console.print(f"    [red]✗[/red] [cyan]{tid}[/cyan]  [red]{detail or 'failed'}[/red]")


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

**Shell:**
- `! <command>` — Run a shell command inline (e.g. `! ls -la`, `! git status`)

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
