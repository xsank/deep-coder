"""Memory skills — /remember and /memory commands."""

from __future__ import annotations

import asyncio
import json
import re
from functools import partial
from typing import Any

from deep_coder.display import console, print_error, print_info, print_success
from deep_coder.memory import Memory, MemoryStore, MemoryType
from deep_coder.models import ModelRole
from deep_coder.skills.base import Skill, SkillContext

_CLASSIFY_PROMPT = """\
You classify user notes into structured memories. Given a user's note, output JSON:

```json
{
  "type": "user|feedback|project|reference",
  "name": "Short Title (2-5 words)",
  "description": "One-line summary for index",
  "content": "Full formatted content"
}
```

Types:
- user: about the user's role, preferences, knowledge, or background
- feedback: guidance on how to work — corrections, confirmations, approach preferences
- project: ongoing work context, deadlines, goals, decisions
- reference: pointers to external resources (URLs, dashboards, tools)

Output ONLY the JSON block. No explanation."""


class RememberSkill(Skill):

    @property
    def name(self) -> str:
        return "/remember"

    @property
    def description(self) -> str:
        return "Save a memory (preference, feedback, reference, or project note)"

    @property
    def usage(self) -> str:
        return "/remember <text>"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        text = arg.strip()
        if not text:
            print_error("Provide something to remember. Usage: /remember <text>")
            return

        print_info("Classifying and saving memory...")

        response = await ctx.client.collect_stream(
            messages=[
                {"role": "system", "content": _CLASSIFY_PROMPT},
                {"role": "user", "content": text},
            ],
            model_role=ModelRole.FLASH,
        )
        content = response.get("content") or ""

        parsed = self._parse_response(content, text)

        store = MemoryStore(cwd=ctx.cwd)
        mem_type = parsed["type"]
        local = mem_type in (MemoryType.PROJECT, MemoryType.REFERENCE)
        memory = Memory(
            id=MemoryStore.slugify(parsed["name"]),
            type=mem_type,
            name=parsed["name"],
            description=parsed["description"],
            content=parsed["content"],
        )
        path = store.save(memory, local=local)
        scope = "project" if local else "global"
        print_success(
            f"Remembered: {memory.name} ({memory.type.value}, {scope})"
        )
        console.print(f"  [dim]{path}[/dim]")
        ctx.orchestrator.invalidate_prompt_cache()

    def _parse_response(self, content: str, original: str) -> dict[str, Any]:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{[^{}]*\"type\"\s*:.*?\})", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return {
                    "type": MemoryType(data.get("type", "feedback")),
                    "name": data.get("name", original[:30]),
                    "description": data.get("description", original[:80]),
                    "content": data.get("content", original),
                }
            except (json.JSONDecodeError, ValueError):
                pass
        words = original.split()[:5]
        return {
            "type": MemoryType.FEEDBACK,
            "name": " ".join(words),
            "description": original[:80],
            "content": original,
        }


class MemorySkill(Skill):

    @property
    def name(self) -> str:
        return "/memory"

    @property
    def description(self) -> str:
        return "List, search, or delete memories"

    @property
    def usage(self) -> str:
        return "/memory [list|search <query>|delete <id>|show <id>]"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        parts = arg.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else "list"
        sub_arg = parts[1].strip() if len(parts) > 1 else ""

        store = MemoryStore(cwd=ctx.cwd)

        if sub == "list":
            self._cmd_list(store, sub_arg)
        elif sub == "search":
            self._cmd_search(store, sub_arg)
        elif sub in ("delete", "rm"):
            await self._cmd_delete(store, sub_arg, ctx)
        elif sub == "show":
            self._cmd_show(store, sub_arg)
        else:
            self._cmd_search(store, arg.strip())

    def _cmd_list(self, store: MemoryStore, type_filter: str) -> None:
        tf: MemoryType | None = None
        if type_filter:
            try:
                tf = MemoryType(type_filter)
            except ValueError:
                print_error(f"Unknown type: {type_filter}. Use: user, feedback, project, reference")
                return

        memories = store.list_all(type_filter=tf)
        if not memories:
            print_info("No memories saved yet.")
            return

        from rich.table import Table
        table = Table(show_header=True, header_style="bold", padding=(0, 1))
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="yellow")
        table.add_column("Name", style="white")
        table.add_column("Description", style="dim")
        table.add_column("Scope", style="dim")

        for m in memories:
            table.add_row(m.id, m.type.value, m.name, m.description[:60], m.source)

        console.print()
        console.print(table)
        console.print(f"\n  [dim]{len(memories)} memories total[/dim]")

    def _cmd_search(self, store: MemoryStore, query: str) -> None:
        if not query:
            print_error("Provide a search query. Usage: /memory search <query>")
            return
        results = store.search(query)
        if not results:
            print_info(f"No memories matching '{query}'.")
            return
        for m in results:
            console.print(
                f"  [cyan]{m.id}[/cyan] [{m.type.value}] "
                f"[bold]{m.name}[/bold] — {m.description[:60]}"
            )

    def _cmd_show(self, store: MemoryStore, memory_id: str) -> None:
        if not memory_id:
            print_error("Provide a memory ID. Usage: /memory show <id>")
            return
        mem = store.get(memory_id)
        if not mem:
            print_error(f"Memory not found: {memory_id}")
            return
        from rich.panel import Panel
        console.print()
        console.print(Panel(
            f"[yellow]{mem.type.value}[/yellow] | "
            f"Created: {mem.created} | Scope: {mem.source}\n\n"
            f"{mem.content}",
            title=f"[bold]{mem.name}[/bold]",
            subtitle=f"[dim]{mem.id}[/dim]",
            border_style="cyan",
        ))

    async def _cmd_delete(self, store: MemoryStore, memory_id: str, ctx: SkillContext) -> None:
        if not memory_id:
            print_error("Provide a memory ID. Usage: /memory delete <id>")
            return
        mem = store.get(memory_id)
        if not mem:
            print_error(f"Memory not found: {memory_id}")
            return

        console.print(f"  Delete [cyan]{mem.name}[/cyan] ({mem.type.value})? [y/N] ", end="")
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, partial(input))
        if answer.strip().lower() in ("y", "yes"):
            store.delete(memory_id)
            print_success(f"Deleted: {memory_id}")
            ctx.orchestrator.invalidate_prompt_cache()
        else:
            print_info("Cancelled.")
