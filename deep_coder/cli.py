"""CLI REPL for Deep Coder."""

from __future__ import annotations

import asyncio
import difflib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from deep_coder.agent.orchestrator import Orchestrator
from deep_coder.client import DeepSeekClient
from deep_coder.config import GLOBAL_CONFIG_DIR, HISTORY_FILE, Config
from deep_coder.display import (
    StatusPanel,
    StreamPrinter,
    console,
    print_banner,
    print_error,
    print_help,
    print_info,
    print_response,
    print_success,
    print_task_status,
    print_warning,
)
from deep_coder.models import get_registry
from deep_coder.skills import SkillRegistry, create_default_skills
from deep_coder.skills.base import SkillContext
from deep_coder.tools.base import create_default_registry

SESSIONS_DIR = GLOBAL_CONFIG_DIR / "sessions"


def _create_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add(Keys.Escape, Keys.Enter)
    def _(event: Any) -> None:
        event.current_buffer.insert_text("\n")

    return kb


class SlashCompleter(Completer):
    """Autocomplete for slash commands — shows suggestions when typing /."""

    BUILTIN_COMMANDS: list[tuple[str, str]] = [
        ("/help", "Show help"),
        ("/exit", "Exit"),
        ("/clear", "Clear history"),
        ("/config", "Show config"),
        ("/model", "Show models"),
        ("/cost", "Usage stats"),
        ("/compact", "Compress history"),
        ("/diff", "Show file changes"),
        ("/undo", "Revert last change"),
        ("/init", "Generate CODER.md"),
        ("/save", "Save session"),
        ("/resume", "Resume session"),
    ]

    def __init__(self, skills: SkillRegistry | None = None) -> None:
        self._entries: list[tuple[str, str]] = list(self.BUILTIN_COMMANDS)
        if skills:
            for skill in skills.list_skills():
                self._entries.append((skill.name, skill.description))

    def get_completions(self, document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor.lstrip()
        if not text.startswith("/") or " " in text:
            return
        for cmd, desc in self._entries:
            if cmd.startswith(text):
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=desc,
                )


class CommandHandler:
    """Handles all slash commands."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        client: DeepSeekClient,
        config: Config,
        status_panel: StatusPanel | None = None,
        skills: SkillRegistry | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.client = client
        self.config = config
        self.status_panel = status_panel
        self.skills = skills

    async def handle(self, command: str) -> bool:
        """Dispatch a slash command. Returns True if the REPL should exit."""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        handler = {
            "/exit": self._cmd_exit,
            "/quit": self._cmd_exit,
            "/q": self._cmd_exit,
            "/help": self._cmd_help,
            "/clear": self._cmd_clear,
            "/config": self._cmd_config,
            "/model": self._cmd_model,
            "/cost": self._cmd_cost,
            "/compact": self._cmd_compact,
            "/diff": self._cmd_diff,
            "/undo": self._cmd_undo,
            "/init": self._cmd_init,
            "/save": self._cmd_save,
            "/resume": self._cmd_resume,
        }.get(cmd)

        if handler:
            return await handler(arg)

        if self.skills:
            skill = self.skills.get(cmd)
            if skill:
                if not self.config.has_api_key:
                    print_error("API key not configured.")
                    return False
                skill_ctx = SkillContext(
                    orchestrator=self.orchestrator,
                    client=self.client,
                    config=self.config,
                    status_panel=self.status_panel,
                    cwd=os.getcwd(),
                )
                try:
                    await skill.execute(arg, skill_ctx)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    print_warning("\nInterrupted.")
                except Exception as e:
                    print_error(f"Skill failed: {e}")
                return False

        print_warning(f"Unknown command: {cmd}. Type /help for available commands.")
        return False

    async def _cmd_exit(self, _: str) -> bool:
        print_info("Goodbye!")
        return True

    async def _cmd_help(self, _: str) -> bool:
        from deep_coder.display import print_help_extended
        print_help_extended()
        return False

    async def _cmd_clear(self, _: str) -> bool:
        self.orchestrator.clear_history()
        self.orchestrator.tool_registry.snapshots.clear()
        print_success("Conversation history and snapshots cleared.")
        return False

    async def _cmd_config(self, _: str) -> bool:
        c = self.config
        print_info("Current Configuration:")
        console.print(f"  Pro model:   {c.model.pro_model}")
        console.print(f"  Flash model: {c.model.flash_model}")
        console.print(f"  Base URL:    {c.model.base_url}")
        console.print(f"  API key:     {'***' + c.model.api_key[-4:] if c.has_api_key else '(not set)'}")
        console.print(f"  Max workers: {c.agent.max_workers}")
        console.print(f"  Temperature: {c.model.temperature}")
        return False

    async def _cmd_model(self, _: str) -> bool:
        registry = get_registry()
        for model in registry.list_models():
            console.print(f"  {model.role.value:6s}  {model.id}  (tools={model.supports_tools})")
        return False

    async def _cmd_cost(self, _: str) -> bool:
        u = self.client.usage
        elapsed = u.elapsed_seconds
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        console.print()
        console.print("[bold]Session Usage Statistics[/bold]")
        console.print(f"  Duration:    {mins}m {secs}s")
        console.print(f"  Requests:    {u.total_requests} total ({u.pro_requests} Pro, {u.flash_requests} Flash)")
        console.print()
        console.print("  [bold blue]Pro (V4 Pro)[/bold blue]")
        console.print(f"    Prompt:     {u.pro_prompt_tokens:,} tokens")
        console.print(f"    Completion: {u.pro_completion_tokens:,} tokens")
        pro_cost = u.estimated_cost("deepseek-v4-pro", u.pro_prompt_tokens, u.pro_completion_tokens)
        console.print(f"    Cost:       ${pro_cost:.4f}")
        console.print()
        console.print("  [bold green]Flash (V4 Flash)[/bold green]")
        console.print(f"    Prompt:     {u.flash_prompt_tokens:,} tokens")
        console.print(f"    Completion: {u.flash_completion_tokens:,} tokens")
        flash_cost = u.estimated_cost("deepseek-v4-flash", u.flash_prompt_tokens, u.flash_completion_tokens)
        console.print(f"    Cost:       ${flash_cost:.4f}")
        console.print()
        console.print(f"  [bold]Total:       ${u.total_cost:.4f}[/bold]")
        console.print()
        return False

    async def _cmd_compact(self, _: str) -> bool:
        if not self.config.has_api_key:
            print_error("API key not configured.")
            return False
        n = len(self.orchestrator.conversation)
        print_info(f"Compacting {n} messages...")
        printer = StreamPrinter(status_panel=self.status_panel)
        await self.orchestrator.compact(on_token=printer.on_token)
        printer.finish()
        if self.status_panel:
            self.status_panel.refresh(force=True)
        print_success(f"Compacted {n} messages into summary.")
        return False

    async def _cmd_diff(self, _: str) -> bool:
        tracker = self.orchestrator.tool_registry.snapshots
        diffs = tracker.get_diffs()
        if not diffs:
            print_info("No file changes in this session.")
            return False
        for fpath, original, current in diffs:
            console.print(f"\n[bold]{fpath}[/bold]")
            old_lines = (original or "").splitlines(keepends=True)
            new_lines = (current or "").splitlines(keepends=True)
            diff = difflib.unified_diff(old_lines, new_lines, fromfile="before", tofile="after")
            diff_text = "".join(diff)
            if diff_text:
                from rich.syntax import Syntax
                console.print(Syntax(diff_text, "diff", theme="monokai"))
            else:
                console.print("  [dim](no changes)[/dim]")
        console.print()
        return False

    async def _cmd_undo(self, _: str) -> bool:
        tracker = self.orchestrator.tool_registry.snapshots
        reverted = tracker.undo_last()
        if reverted:
            print_success(f"Reverted: {reverted}")
        else:
            print_warning("Nothing to undo.")
        return False

    async def _cmd_init(self, _: str) -> bool:
        if not self.config.has_api_key:
            print_error("API key not configured.")
            return False
        cwd = os.getcwd()
        coder_md = Path(cwd) / "CODER.md"
        if coder_md.exists():
            print_warning("CODER.md already exists. Delete it first to regenerate.")
            return False

        print_info("Scanning project and generating CODER.md...")
        printer = StreamPrinter(status_panel=self.status_panel)
        result = await self.orchestrator.process(
            "Analyze this project directory. Read key files (README, config, main source files). "
            "Then generate a CODER.md file in the project root that documents: "
            "1) Project overview, 2) Tech stack and dependencies, "
            "3) Directory structure, 4) Key conventions, "
            "5) Build/test/run commands. Keep it concise and useful for an AI coding assistant.",
            on_token=printer.on_token,
        )
        printer.finish()
        if self.status_panel:
            self.status_panel.refresh(force=True)
        if not coder_md.exists():
            print_response(result)
        else:
            print_success(f"Generated {coder_md}")
        return False

    async def _cmd_save(self, name: str) -> bool:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session_name = name.strip() or f"session-{int(time.time())}"
        session_file = SESSIONS_DIR / f"{session_name}.json"
        data = {
            "name": session_name,
            "cwd": os.getcwd(),
            "timestamp": time.time(),
            "conversation": self.orchestrator.export_conversation(),
        }
        session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print_success(f"Session saved: {session_file}")
        return False

    async def _cmd_resume(self, name: str) -> bool:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        if not name.strip():
            sessions = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not sessions:
                print_warning("No saved sessions found.")
                return False
            console.print("[bold]Saved sessions:[/bold]")
            for i, s in enumerate(sessions[:10]):
                data = json.loads(s.read_text())
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(data.get("timestamp", 0)))
                n_msgs = len(data.get("conversation", []))
                console.print(f"  {s.stem:30s}  {ts}  ({n_msgs} messages)")
            console.print("\nUsage: /resume <session-name>")
            return False

        session_file = SESSIONS_DIR / f"{name.strip()}.json"
        if not session_file.exists():
            print_error(f"Session not found: {name}")
            return False

        data = json.loads(session_file.read_text())
        self.orchestrator.import_conversation(data.get("conversation", []))
        n = len(data.get("conversation", []))
        print_success(f"Resumed session '{name}' ({n} messages)")
        return False


async def _ask_approval(tool_name: str, arguments: str) -> bool:
    """Ask user for approval before executing a write/shell tool."""
    console.print(f"\n  [warning]Approval required:[/warning] [tool]{tool_name}[/tool]")
    try:
        args = json.loads(arguments)
        if tool_name == "exec_shell":
            console.print(f"    Command: {args.get('command', '?')}")
        elif "file_path" in args:
            console.print(f"    File: {args['file_path']}")
    except (json.JSONDecodeError, KeyError):
        pass
    console.print("  [dim]Allow? [y]es / [n]o / [a]lways[/dim] ", end="")

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, lambda: input().strip().lower())
    return answer in ("y", "yes", "a", "always")


_INTERACTIVE_CMDS = frozenset({
    "vim", "vi", "nvim", "nano", "emacs", "emacsclient",
    "less", "more", "man",
    "htop", "top", "btop",
    "ssh", "tmux", "screen",
})


def _is_interactive_command(command: str) -> bool:
    for token in command.split():
        if "=" in token:
            continue
        return os.path.basename(token) in _INTERACTIVE_CMDS
    return False


async def _run_shell_command(command: str) -> None:
    """Execute a shell command and display output inline."""
    console.print(f"  [dim]$[/dim] {command}")
    loop = asyncio.get_event_loop()

    if _is_interactive_command(command):
        try:
            returncode = await loop.run_in_executor(
                None,
                lambda: subprocess.run(command, shell=True).returncode,
            )
            if returncode != 0:
                console.print(f"  [dim]exit code {returncode}[/dim]")
        except Exception as e:
            print_error(f"Shell error: {e}")
        return

    try:
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            ),
        )
        if result.stdout:
            console.print(result.stdout, end="", highlight=False)
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]", end="", highlight=False)
        if result.returncode != 0:
            console.print(f"  [dim]exit code {result.returncode}[/dim]")
    except subprocess.TimeoutExpired:
        print_error("Command timed out (120s limit).")
    except Exception as e:
        print_error(f"Shell error: {e}")


_DOUBLE_CTRL_C_WINDOW = 2.0


async def _run_repl(config: Config) -> None:
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    client = DeepSeekClient(config)
    tool_registry = create_default_registry()
    orchestrator = Orchestrator(client, config, tool_registry)
    orchestrator.set_cwd(os.getcwd())

    status_panel = StatusPanel(client.usage)
    skills = create_default_skills()
    cmd_handler = CommandHandler(orchestrator, client, config, status_panel, skills)
    completer = SlashCompleter(skills)

    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        key_bindings=_create_key_bindings(),
        completer=completer,
        complete_while_typing=True,
        multiline=False,
    )

    print_banner()

    if not config.has_api_key:
        print_warning(
            "No API key configured. Set DEEPSEEK_API_KEY environment variable "
            "or add it to .deep-coder/config.toml"
        )

    last_interrupt = 0.0

    while True:
        try:
            user_input = await session.prompt_async(
                "you> ",
            )
            last_interrupt = 0.0
        except KeyboardInterrupt:
            now = time.time()
            if now - last_interrupt < _DOUBLE_CTRL_C_WINDOW:
                print_info("\nGoodbye!")
                break
            last_interrupt = now
            print_warning("\nPress Ctrl+C again to exit.")
            continue
        except EOFError:
            print_info("\nGoodbye!")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.startswith("/"):
            should_exit = await cmd_handler.handle(text)
            if should_exit:
                break
            continue

        if text.startswith("!"):
            shell_cmd = text[1:].strip()
            if shell_cmd:
                await _run_shell_command(shell_cmd)
            else:
                print_warning("Usage: ! <command>  (e.g. ! ls -la)")
            continue

        if not config.has_api_key:
            print_error("API key not configured. Set DEEPSEEK_API_KEY or use /config.")
            continue

        printer = StreamPrinter(status_panel=status_panel)

        async def on_status(task: Any, status: str) -> None:
            task_id = task.id if task and hasattr(task, "id") else None
            print_task_status(task_id, status)

        try:
            result = await orchestrator.process(
                text,
                on_token=printer.on_token,
                on_status=on_status,
            )
            printer.finish()
            status_panel.refresh(force=True)

            if not printer.get_content() and result:
                print_response(result)

        except (KeyboardInterrupt, asyncio.CancelledError):
            printer.finish()
            print_warning("\nInterrupted.")
            last_interrupt = time.time()
        except Exception as e:
            printer.finish()
            print_error(f"Request failed: {e}")


def main() -> None:
    """Entry point for the CLI."""
    if "--help" in sys.argv or "-h" in sys.argv:
        console.print("Usage: deep-coder [options]")
        console.print()
        console.print("The most cost-effective code assistant tool based on DeepSeek V4.")
        console.print()
        console.print("Options:")
        console.print("  -h, --help     Show this help message")
        console.print("  --version      Show version")
        console.print()
        console.print("Environment variables:")
        console.print("  DEEPSEEK_API_KEY       Your DeepSeek API key")
        console.print("  DEEPSEEK_BASE_URL      API base URL (default: https://api.deepseek.com)")
        console.print("  DEEPSEEK_PRO_MODEL     Pro model ID (default: deepseek-v4-pro)")
        console.print("  DEEPSEEK_FLASH_MODEL   Flash model ID (default: deepseek-v4-flash)")
        return

    if "--version" in sys.argv:
        from deep_coder import __version__
        console.print(f"deep-coder {__version__}")
        return

    config = Config.load()
    try:
        asyncio.run(_run_repl(config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
