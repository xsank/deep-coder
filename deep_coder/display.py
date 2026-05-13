"""Rich console output for Deep Coder — streaming, spinners, tool call visualization."""

from __future__ import annotations

import asyncio
import difflib
import json
import os
import shutil
import time
from typing import TYPE_CHECKING, Any

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    from deep_coder.client import UsageStats

THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "tool": "magenta",
        "model.pro": "bold blue",
        "model.flash": "bold green",
        "dim": "dim white",
    }
)

console = Console(theme=THEME)


def print_banner() -> None:
    """Print a geek-style cyberpunk splash screen for Deep Coder."""
    import platform

    from deep_coder import __version__

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
        ("  [green]✓[/] Orchestrator Core   [dim]Pro V4[/]         [bold green]online[/]", 0.04),
        ("  [green]✓[/] Worker Swarm        [dim]Flash V4 ×5[/]    [bold green]online[/]", 0.04),
        ("  [green]✓[/] Tool Registry       [dim]19 tools[/]       [bold green]loaded[/]", 0.03),
        ("  [green]✓[/] Skill Registry      [dim]9 skills[/]       [bold green]loaded[/]", 0.03),
        ("  [green]✓[/] API Connection      [dim]deepseek.com[/]   [bold green]connected[/]", 0.04),
        ("", 0.03),
        (
            f"  [bold green]Ready.[/]  [dim]{platform.system()} {platform.machine()}  ·  {sn}[/]",
            0.05,
        ),
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
        [
            ("/help", "commands"),
            ("/review", "AI review"),
            ("/commit", "commit msg"),
            ("/fix", "auto-fix"),
        ],
        [
            ("/think", "reasoning"),
            ("/explain", "explain"),
            ("/pr", "PR desc"),
            ("/test", "run tests"),
        ],
        [("/remember", "save note"), ("/memory", "manage")],
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


_EXT_TO_LEXER: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".sh": "bash",
    ".zsh": "bash",
    ".fish": "fish",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".md": "markdown",
    ".txt": "text",
    ".cfg": "ini",
    ".ini": "ini",
    ".dockerfile": "dockerfile",
    ".lua": "lua",
}


def print_file_diff(
    file_path: str,
    old_content: str | None,
    new_content: str | None,
    context_lines: int = 3,
) -> None:
    """Render a Claude-style inline diff with syntax-aware coloring."""
    short_path = file_path
    try:
        short_path = os.path.relpath(file_path)
    except ValueError:
        pass

    if old_content is None and new_content is not None:
        action = "Write"
    elif old_content is not None and new_content is None:
        action = "Delete"
    elif old_content == new_content:
        return
    else:
        action = "Update"

    old_lines = (old_content or "").splitlines(keepends=True)
    new_lines = (new_content or "").splitlines(keepends=True)

    diff = list(difflib.unified_diff(old_lines, new_lines))
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))

    summary_parts: list[str] = []
    if added:
        summary_parts.append(f"Added {added} line{'s' if added != 1 else ''}")
    if removed:
        summary_parts.append(f"Removed {removed} line{'s' if removed != 1 else ''}")
    summary = ", ".join(summary_parts) if summary_parts else "No changes"

    console.print(f"\n  [bold bright_cyan]⏺ {action}[/bold bright_cyan]([cyan]{short_path}[/cyan])")
    console.print(f"  [dim]⎿  {summary}[/dim]")

    import re

    ext = os.path.splitext(file_path)[1].lower()
    lexer = _EXT_TO_LEXER.get(ext, "text")
    highlighter = Syntax("", lexer, theme="monokai", background_color="default")

    def _hl(code: str) -> Text:
        t = highlighter.highlight(code)
        t.rstrip()
        return t

    diff = list(difflib.unified_diff(old_lines, new_lines, n=context_lines))
    if len(diff) <= 2:
        return

    old_ln = 0
    new_ln = 0
    first_hunk = True

    for line in diff[2:]:
        line_text = line.rstrip("\n")

        if line.startswith("@@"):
            m = re.match(r"@@ -(\d+)", line)
            if m:
                old_ln = int(m.group(1))
                new_ln = old_ln
                match_new = re.search(r"\+(\d+)", line)
                if match_new:
                    new_ln = int(match_new.group(1))
            if not first_hunk:
                console.print("      [dim]...[/dim]")
            first_hunk = False
        elif line.startswith("-"):
            code = line_text[1:]
            rendered = Text(f"      {old_ln:>5d} - ", style="red")
            rendered.append_text(_hl(code))
            console.print(rendered)
            old_ln += 1
        elif line.startswith("+"):
            code = line_text[1:]
            rendered = Text(f"      {new_ln:>5d} + ", style="green")
            rendered.append_text(_hl(code))
            console.print(rendered)
            new_ln += 1
        else:
            code = line_text[1:] if line_text.startswith(" ") else line_text
            rendered = Text(f"      {new_ln:>5d}   ", style="dim")
            rendered.append_text(_hl(code))
            console.print(rendered)
            old_ln += 1
            new_ln += 1

    console.print()


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
    "verifying": ("red", "Pro"),
    "reporting": ("green", "Pro"),
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


class ReasoningStreamDisplay:
    """Shows reasoning tokens in real-time with elapsed timer."""

    MAX_DISPLAY_CHARS = 200

    def __init__(self, phase: str = "planning") -> None:
        self._phase = phase
        self._start = 0.0
        self._buffer: list[str] = []
        self._total_chars = 0
        self._live: Live | None = None
        self._timer_task: asyncio.Task[None] | None = None

    def _render(self) -> Text:
        elapsed = time.monotonic() - self._start
        t = _format_elapsed(elapsed)
        color, model = _PHASE_STYLES.get(self._phase, ("cyan", "Pro"))

        line = Text()
        line.append("\n  ")
        line.append("●", style=color)
        line.append(f" {self._phase.upper()}", style="bold")
        line.append(f" ({model})", style="dim")
        line.append(f"  {t}", style="dim")

        tail = "".join(self._buffer)
        if len(tail) > self.MAX_DISPLAY_CHARS:
            tail = "..." + tail[-self.MAX_DISPLAY_CHARS :]
        if tail:
            display_lines = tail.strip().split("\n")
            for dl in display_lines[-3:]:
                line.append("\n    ")
                line.append(dl.strip(), style="dim italic")
        return line

    async def _timer_loop(self) -> None:
        try:
            while True:
                if self._live:
                    self._live.update(self._render())
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def start(self) -> None:
        self._start = time.monotonic()
        self._live = Live(
            self._render(),
            console=console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()
        self._timer_task = asyncio.create_task(self._timer_loop())

    async def on_reasoning(self, token: str) -> None:
        self._buffer.append(token)
        self._total_chars += len(token)
        if self._live:
            self._live.update(self._render())

    async def stop(self, interrupted: bool = False) -> None:
        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
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
        color, model = _PHASE_STYLES.get(self._phase, ("cyan", "Pro"))
        int_s = " [yellow]interrupted[/yellow]" if interrupted else ""
        console.print(
            f"\n  [{color}]●[/{color}] [bold]{self._phase.upper()}[/bold]"
            f" [dim]({model})[/dim]  [dim]{t}[/dim]{int_s}"
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


def summarize_tool_args(tool_name: str, arguments_json: str) -> str:
    """Extract the key argument from a tool call for display."""
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except (json.JSONDecodeError, TypeError):
        return ""
    if tool_name in (
        "read_file",
        "write_file",
        "edit_file",
        "multi_edit_file",
        "insert_text",
        "delete_file",
    ):
        return os.path.basename(args.get("file_path", ""))
    if tool_name == "move_file":
        src = os.path.basename(args.get("source", ""))
        dst = os.path.basename(args.get("destination", ""))
        return f"{src} → {dst}" if src else ""
    if tool_name == "exec_shell":
        cmd = args.get("command", "")
        return cmd[:50] + ("..." if len(cmd) > 50 else "")
    if tool_name == "grep_files":
        pat = args.get("pattern", "")
        glb = args.get("glob", "")
        s = f'"{pat}"'
        if glb:
            s += f" in {glb}"
        return s[:50]
    if tool_name == "glob_files":
        return args.get("pattern", "")[:50]
    if tool_name == "list_files":
        return args.get("path", ".")
    if tool_name == "git_commit":
        return args.get("message", "")[:40]
    if tool_name == "git_checkout":
        return args.get("branch", "")
    if tool_name == "web_search":
        return args.get("query", "")[:50]
    if tool_name == "web_fetch":
        from urllib.parse import urlparse

        url = args.get("url", "")
        parsed = urlparse(url)
        return parsed.netloc or url[:50]
    return ""


def summarize_tool_result(
    tool_name: str,
    content: str,
    success: bool,
) -> str:
    """Create a brief summary of a tool result for display."""
    if not success:
        return "failed"
    if tool_name == "read_file":
        n = content.count("\n")
        return f"{n} lines" if n > 0 else "ok"
    if tool_name == "grep_files":
        n = content.count("\n")
        return f"{n} matches" if n > 0 else "0 matches"
    if tool_name in ("glob_files", "list_files"):
        n = content.count("\n")
        return f"{n} files" if n > 0 else "empty"
    if tool_name == "exec_shell":
        if "exit code:" in content.lower():
            return "error"
        return "ok"
    if tool_name == "web_search":
        n = content.count("\n\n")
        return f"{n} results" if n > 0 else "0 results"
    if tool_name == "web_fetch":
        return f"{len(content)} chars"
    return "ok"


class TaskProgressDisplay:
    """Compact inline progress for parallel task execution with animated header."""

    REFRESH_PER_SECOND = 4

    def __init__(self, detail: str = "") -> None:
        self._task_states: dict[str, dict[str, str]] = {}
        self._task_tool_history: dict[str, list[dict[str, str]]] = {}
        self._task_start_times: dict[str, float] = {}
        self._task_end_times: dict[str, float] = {}
        self._live: Live | None = None
        self._timer_task: asyncio.Task[None] | None = None
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
            desc = state.get("desc", "")
            history = self._task_tool_history.get(tid, [])

            task_time = ""
            if status in ("running", "retrying"):
                icon = "⟳"
                icon_style = "bold yellow"
                info = detail or "analyzing"
                info_style = "yellow"
                if tid in self._task_start_times:
                    te = time.monotonic() - self._task_start_times[tid]
                    task_time = f"  {_format_elapsed(te)}"
            elif status == "completed":
                icon = "✓"
                icon_style = "bold green"
                n_tools = len(history)
                info = f"done ({n_tools} tools)" if n_tools > 0 else "done"
                info_style = "green"
                s = self._task_start_times.get(tid, 0)
                e = self._task_end_times.get(tid, 0)
                if s and e:
                    task_time = f"  {_format_elapsed(e - s)}"
            elif status == "failed":
                icon = "✗"
                icon_style = "bold red"
                info = detail or "failed"
                info_style = "red"
                s = self._task_start_times.get(tid, 0)
                e = self._task_end_times.get(tid, 0)
                if s and e:
                    task_time = f"  {_format_elapsed(e - s)}"
            else:
                icon = "○"
                icon_style = "dim"
                info = desc if desc else "waiting"
                info_style = "dim"

            result.append("    ")
            result.append(icon, style=icon_style)
            result.append(f" {tid}", style="cyan")
            result.append(f"  {info}", style=info_style)
            if task_time:
                result.append(task_time, style="dim")
            result.append("\n")

            if status in ("running", "retrying") and history:
                recent = history[-3:]
                for i, entry in enumerate(recent):
                    is_last = i == len(recent) - 1
                    branch = "└─" if is_last else "├─"
                    if entry["status"] == "running":
                        t_icon = "⟳"
                        t_style = "yellow"
                    elif entry["status"] == "done":
                        t_icon = "✓"
                        t_style = "green"
                    else:
                        t_icon = "✗"
                        t_style = "red"
                    line = entry["tool"]
                    if entry["args"]:
                        line += f": {entry['args']}"
                    if entry["result"]:
                        line += f" ({entry['result']})"
                    result.append(f"      {branch} ")
                    result.append(t_icon, style=t_style)
                    result.append(f" {line}", style="dim")
                    result.append("\n")

        return result

    def add_tool_action(
        self,
        task_id: str,
        tool_name: str,
        args_summary: str,
        status: str,
        result_brief: str = "",
    ) -> None:
        """Record a tool action for display. status: start|done|failed."""
        history = self._task_tool_history.setdefault(task_id, [])
        if status == "start":
            history.append(
                {
                    "tool": tool_name,
                    "args": args_summary,
                    "status": "running",
                    "result": "",
                }
            )
        else:
            for entry in reversed(history):
                if entry["tool"] == tool_name and entry["status"] == "running":
                    entry["status"] = status
                    entry["result"] = result_brief
                    break
        if self._live:
            self._live.update(self._build_renderable())

    async def _timer_loop(self) -> None:
        try:
            while True:
                if self._live:
                    self._live.update(self._build_renderable())
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def start(self, tasks: list[Any]) -> None:
        self._start_time = time.monotonic()
        for t in tasks:
            self._task_states[t.id] = {
                "status": "pending",
                "desc": t.description[:40],
                "detail": "",
            }
            self._task_tool_history[t.id] = []
        self._live = Live(
            self._build_renderable(),
            console=console,
            refresh_per_second=self.REFRESH_PER_SECOND,
            transient=True,
        )
        self._live.start()
        self._timer_task = asyncio.create_task(self._timer_loop())

    async def update(self, task_id: str, status: str, detail: str = "") -> None:
        async with self._lock:
            if task_id in self._task_states:
                prev = self._task_states[task_id]["status"]
                self._task_states[task_id]["status"] = status
                if detail:
                    self._task_states[task_id]["detail"] = detail
                if status in ("running", "retrying") and prev == "pending":
                    self._task_start_times[task_id] = time.monotonic()
                if status in ("completed", "failed") and task_id not in self._task_end_times:
                    self._task_end_times[task_id] = time.monotonic()
            if self._live:
                self._live.update(self._build_renderable())

    def pause(self) -> None:
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None
        if self._live:
            self._live.stop()

    def resume(self) -> None:
        if self._live:
            self._live.start()
            self._timer_task = asyncio.create_task(self._timer_loop())

    async def stop(self) -> None:
        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except (asyncio.CancelledError, Exception):
                pass
            self._timer_task = None
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
            history = self._task_tool_history.get(tid, [])
            s = self._task_start_times.get(tid, 0)
            e = self._task_end_times.get(tid, 0)
            task_time = f"  [dim]{_format_elapsed(e - s)}[/dim]" if s and e else ""
            if status == "completed":
                n = len(history)
                ts = f" ({n} tools)" if n > 0 else ""
                console.print(
                    f"    [green]✓[/green] [cyan]{tid}[/cyan]  [green]done{ts}[/green]{task_time}",
                )
            elif status == "failed":
                detail = state.get("detail", "")
                console.print(
                    f"    [red]✗[/red] [cyan]{tid}[/cyan]"
                    f"  [red]{detail or 'failed'}[/red]{task_time}",
                )


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
- `/remember <text>` — Save a memory (preference, feedback, reference, note)
- `/memory [list|search|delete|show]` — Manage saved memories

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
    """Accumulates streaming tokens and renders as live Markdown.

    Optional *phase* support: pass ``phase="verifying"`` to show a
    PhaseSpinner-style animated header with real-time elapsed time while
    waiting for the first token, then seamlessly switch to Markdown streaming.
    """

    _UPDATE_INTERVAL = 0.08

    def __init__(
        self,
        status_panel: StatusPanel | None = None,
        phase: str = "",
        phase_detail: str = "",
        skip_spinner: bool = False,
    ) -> None:
        self._buffer: list[str] = []
        self._status_panel = status_panel
        self._live: Live | None = None
        self._last_update = 0.0
        self._committed_len = 0
        # Phase header support
        self._phase = phase
        self._phase_detail = phase_detail.rstrip(".")
        self._start = 0.0
        self._phase_live: Live | None = None
        self._phase_timer: asyncio.Task[None] | None = None
        self._header_committed = False
        self._streaming_timer: asyncio.Task[None] | None = None
        if phase and not skip_spinner:
            self._start_phase()
        elif phase:
            self._start = time.monotonic()

    def _render_phase(self) -> Text:
        color, model = _PHASE_STYLES.get(self._phase, ("cyan", ""))
        elapsed = time.monotonic() - self._start
        n = int(elapsed / 0.5) % 3 + 1
        t = _format_elapsed(elapsed)
        line = Text()
        line.append("\n  ")
        line.append("●", style=color)
        line.append(f" {self._phase.upper()}", style="bold")
        line.append(f" ({model})", style="dim")
        if self._phase_detail:
            line.append(f"  {self._phase_detail}", style="dim")
        line.append("." * n, style="dim")
        line.append(f"  {t}", style="dim")
        return line

    def _start_phase(self) -> None:
        self._start = time.monotonic()
        self._phase_live = Live(
            self._render_phase(),
            console=console,
            refresh_per_second=4,
            transient=True,
        )
        self._phase_live.start()
        self._phase_timer = asyncio.create_task(self._phase_loop())

    async def _phase_loop(self) -> None:
        try:
            while True:
                if self._phase_live:
                    self._phase_live.update(self._render_phase())
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            pass

    def _stop_phase(self) -> None:
        if self._phase_timer:
            self._phase_timer.cancel()
            self._phase_timer = None
        if self._phase_live:
            try:
                self._phase_live.stop()
            except Exception:
                pass
            self._phase_live = None

    def _print_phase_header(self) -> None:
        """Commit phase header as static console output."""
        if not self._phase or self._header_committed:
            return
        self._header_committed = True
        elapsed = time.monotonic() - self._start
        t = _format_elapsed(elapsed)
        color, model = _PHASE_STYLES.get(self._phase, ("cyan", ""))
        detail_s = f"  [dim]{self._phase_detail}[/dim]" if self._phase_detail else ""
        console.print(
            f"\n  [{color}]●[/{color}] [bold]{self._phase.upper()}[/bold]"
            f" [dim]({model})[/dim]{detail_s}  [dim]{t}[/dim]"
        )

    def _build_renderable(self) -> Any:
        """Build combined renderable: phase header + markdown content."""
        parts: list[Any] = []
        if self._phase and not self._header_committed:
            parts.append(self._render_phase())
        pending = self._get_pending()
        if pending.strip():
            parts.append(Markdown(pending))
        if not parts:
            return Text("")
        if len(parts) == 1:
            return parts[0]
        return Group(*parts)

    async def _streaming_timer_loop(self) -> None:
        """Keep Live updated for elapsed time changes during streaming."""
        try:
            while True:
                if self._live:
                    self._live.update(self._build_renderable())
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    def _get_pending(self) -> str:
        return self.get_content()[self._committed_len :]

    def _safe_to_flush(self) -> bool:
        pending = self._get_pending()
        if not pending.rstrip(" \t").endswith("\n"):
            return False
        return not self._has_open_fence(pending)

    @staticmethod
    def _has_open_fence(text: str) -> bool:
        in_fence = False
        fence_char = ""
        fence_len = 0
        for line in text.split("\n"):
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent > 3:
                continue
            if not in_fence:
                if stripped.startswith("```") or stripped.startswith("~~~"):
                    in_fence = True
                    fence_char = stripped[0]
                    fence_len = 0
                    for ch in stripped:
                        if ch == fence_char:
                            fence_len += 1
                        else:
                            break
            else:
                if stripped.startswith(fence_char * fence_len):
                    rest = stripped[fence_len:].strip()
                    if not rest:
                        in_fence = False
        return in_fence

    def _find_safe_split(self, pending: str) -> int:
        in_fence = False
        fence_char = ""
        fence_len = 0
        last_safe = 0
        pos = 0
        for line in pending.split("\n"):
            line_end = pos + len(line) + 1
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent <= 3:
                if not in_fence:
                    if stripped.startswith("```") or stripped.startswith("~~~"):
                        in_fence = True
                        fence_char = stripped[0]
                        fence_len = 0
                        for ch in stripped:
                            if ch == fence_char:
                                fence_len += 1
                            else:
                                break
                    else:
                        last_safe = line_end
                else:
                    if stripped.startswith(fence_char * fence_len):
                        rest = stripped[fence_len:].strip()
                        if not rest:
                            in_fence = False
                            last_safe = line_end
            elif not in_fence:
                last_safe = line_end
            pos = line_end
        if in_fence and last_safe > 0:
            return last_safe
        return 0

    def _flush_partial(self, n: int) -> None:
        """Flush the first *n* characters of pending content."""
        if self._streaming_timer:
            self._streaming_timer.cancel()
            self._streaming_timer = None
        if self._live:
            self._live.stop()
            self._live = None
        self._print_phase_header()
        chunk = self._get_pending()[:n]
        if chunk.strip():
            console.print()
            console.print(Markdown(chunk))
        self._committed_len += n

    def _flush(self) -> None:
        if self._streaming_timer:
            self._streaming_timer.cancel()
            self._streaming_timer = None
        if self._live:
            self._live.stop()
            self._live = None
        self._print_phase_header()
        pending = self._get_pending()
        if pending.strip():
            console.print()
            console.print(Markdown(pending))
        self._committed_len = len(self.get_content())

    async def on_token(self, token: str) -> None:
        if self._phase_live:
            self._stop_phase()
        self._buffer.append(token)

        pending = self._get_pending()
        term_h = shutil.get_terminal_size((80, 24)).lines
        needs_flush = pending.count("\n") >= term_h - 8 or len(pending) > 3000

        if needs_flush:
            if self._safe_to_flush():
                self._flush()
                return
            # Inside a code fence — flush content before the fence
            split = self._find_safe_split(pending)
            if split > 0:
                self._flush_partial(split)
                return

        if not self._live:
            self._live = Live(
                self._build_renderable(),
                console=console,
                refresh_per_second=8,
                transient=True,
            )
            self._live.start()
            if self._phase and not self._header_committed:
                self._streaming_timer = asyncio.create_task(self._streaming_timer_loop())
        now = time.monotonic()
        if now - self._last_update >= self._UPDATE_INTERVAL:
            self._last_update = now
            self._live.update(self._build_renderable())
        if self._status_panel:
            self._status_panel.refresh()

    def get_content(self) -> str:
        return "".join(self._buffer)

    def finish(self) -> None:
        if self._streaming_timer:
            self._streaming_timer.cancel()
            self._streaming_timer = None
        if self._phase_live:
            self._stop_phase()
        if self._live:
            self._live.stop()
            self._live = None
        self._print_phase_header()
        pending = self._get_pending()
        if pending.strip():
            console.print()
            console.print(Markdown(pending))
            console.print()
        elif self._committed_len > 0:
            console.print()


class StatusPanel:
    """Token usage tracker (no longer renders an overlay)."""

    def __init__(self, usage: UsageStats) -> None:
        self._usage = usage

    def refresh(self, force: bool = False) -> None:
        pass
