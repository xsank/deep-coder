"""CLI REPL for Deep Coder."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from deep_coder.agent.orchestrator import Orchestrator
from deep_coder.client import DeepSeekClient
from deep_coder.config import GLOBAL_CONFIG_DIR, HISTORY_FILE, Config
from deep_coder.display import (
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
from deep_coder.tools.base import create_default_registry


def _create_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add(Keys.Escape, Keys.Enter)
    def _(event: any) -> None:
        event.current_buffer.insert_text("\n")

    return kb


async def _handle_slash_command(command: str, orchestrator: Orchestrator, config: Config) -> bool:
    """Handle slash commands. Returns True if the command was handled."""
    cmd = command.strip().lower()

    if cmd in ("/exit", "/quit", "/q"):
        print_info("Goodbye!")
        return True

    if cmd == "/help":
        print_help()
        return False

    if cmd == "/clear":
        orchestrator.clear_history()
        print_success("Conversation history cleared.")
        return False

    if cmd == "/config":
        print_info("Current Configuration:")
        console.print(f"  Pro model:   {config.model.pro_model}")
        console.print(f"  Flash model: {config.model.flash_model}")
        console.print(f"  Base URL:    {config.model.base_url}")
        console.print(f"  API key:     {'***' + config.model.api_key[-4:] if config.has_api_key else '(not set)'}")
        console.print(f"  Max workers: {config.agent.max_workers}")
        console.print(f"  Temperature: {config.model.temperature}")
        return False

    if cmd == "/model":
        registry = get_registry()
        for model in registry.list_models():
            console.print(f"  {model.role.value:6s}  {model.id}  (tools={model.supports_tools})")
        return False

    print_warning(f"Unknown command: {command}. Type /help for available commands.")
    return False


async def _run_repl(config: Config) -> None:
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        key_bindings=_create_key_bindings(),
        multiline=False,
    )

    client = DeepSeekClient(config)
    tool_registry = create_default_registry()
    orchestrator = Orchestrator(client, config, tool_registry)
    orchestrator.set_cwd(os.getcwd())

    print_banner()

    if not config.has_api_key:
        print_warning(
            "No API key configured. Set DEEPSEEK_API_KEY environment variable "
            "or add it to ~/.deep-coder/config.toml"
        )

    while True:
        try:
            user_input = await session.prompt_async(
                "you> ",
                vi_mode=False,
            )
        except (EOFError, KeyboardInterrupt):
            print_info("\nGoodbye!")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.startswith("/"):
            should_exit = await _handle_slash_command(text, orchestrator, config)
            if should_exit:
                break
            continue

        if not config.has_api_key:
            print_error("API key not configured. Set DEEPSEEK_API_KEY or use /config.")
            continue

        printer = StreamPrinter()

        async def on_status(task: any, status: str) -> None:
            task_id = task.id if task and hasattr(task, "id") else None
            print_task_status(task_id, status)

        try:
            with console.status("[bold cyan]Thinking...", spinner="dots"):
                pass

            result = await orchestrator.process(
                text,
                on_token=printer.on_token,
                on_status=on_status,
            )
            printer.finish()

            if not printer.get_content():
                print_response(result)

        except KeyboardInterrupt:
            printer.finish()
            print_warning("\nInterrupted.")
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
    asyncio.run(_run_repl(config))


if __name__ == "__main__":
    main()
