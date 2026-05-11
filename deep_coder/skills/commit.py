"""Smart commit skill with AI-generated messages."""

from __future__ import annotations

import asyncio

from deep_coder.display import console, print_error, print_info, print_success, print_warning
from deep_coder.models import ModelRole
from deep_coder.skills.base import Skill, SkillContext


class CommitSkill(Skill):
    @property
    def name(self) -> str:
        return "/commit"

    @property
    def description(self) -> str:
        return "Generate AI commit message from staged changes and commit"

    @property
    def usage(self) -> str:
        return "/commit [hint]"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        code, staged_diff, _ = await self._run_git("diff", "--cached", cwd=ctx.cwd)
        if not staged_diff.strip():
            print_warning("No staged changes. Stage files with `git add` first.")
            return

        code, stat, _ = await self._run_git("diff", "--cached", "--stat", cwd=ctx.cwd)
        print_info(f"Staged changes:\n{stat}")

        hint = arg.strip()
        hint_line = f"\nHint from developer: {hint}" if hint else ""

        prompt = (
            f"Generate a git commit message for the following staged changes.\n\n"
            f"```diff\n{staged_diff[:8000]}\n```\n{hint_line}\n\n"
            f"Rules:\n"
            f"- Use conventional commit format: type(scope): subject\n"
            f"- Types: feat, fix, refactor, docs, test, chore, perf, style, ci\n"
            f"- Subject line: imperative mood, lowercase, no period, max 72 chars\n"
            f"- Add a blank line then a body (2-3 sentences) explaining WHY, not WHAT\n"
            f"- Output ONLY the commit message, nothing else"
        )

        response = await ctx.client.collect_stream(
            messages=[
                {"role": "system", "content": "You generate concise, precise git commit messages. Output only the message."},
                {"role": "user", "content": prompt},
            ],
            model_role=ModelRole.FLASH,
        )
        message = (response.get("content") or "").strip()
        if ctx.status_panel:
            ctx.status_panel.refresh(force=True)

        if not message:
            print_error("Failed to generate commit message.")
            return

        message = message.strip("`").strip()
        if message.startswith("```"):
            message = message.split("\n", 1)[-1]
        if message.endswith("```"):
            message = message.rsplit("```", 1)[0]
        message = message.strip()

        console.print()
        console.print("[bold]Generated commit message:[/bold]")
        console.print()
        for line in message.split("\n"):
            console.print(f"  {line}")
        console.print()
        console.print("[dim]Commit with this message? [y]es / [n]o[/dim] ", end="")

        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, lambda: input().strip().lower())

        if answer in ("y", "yes"):
            code, out, err = await self._run_git("commit", "-m", message, cwd=ctx.cwd)
            if code != 0:
                print_error(f"Commit failed: {err}")
            else:
                print_success("Committed successfully.")
        else:
            print_info("Commit cancelled.")
