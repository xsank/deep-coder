"""Fix errors from pasted error messages or tracebacks."""

from __future__ import annotations

from deep_coder.display import print_error, print_info
from deep_coder.skills.base import Skill, SkillContext


class FixSkill(Skill):
    @property
    def name(self) -> str:
        return "/fix"

    @property
    def description(self) -> str:
        return "Analyze an error message and fix the root cause"

    @property
    def usage(self) -> str:
        return "/fix <error message or traceback>"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        error_text = arg.strip()
        if not error_text:
            print_error("Provide an error message or traceback. Usage: /fix <error>")
            return

        print_info("Analyzing error and applying fix...")

        prompt = (
            f"## Error Fix Request\n\n"
            f"The user encountered this error:\n\n"
            f"```\n{error_text}\n```\n\n"
            f"Instructions:\n"
            f"1. Read the relevant source files mentioned in the traceback\n"
            f"2. Identify the root cause\n"
            f"3. Apply the fix by editing the source files\n"
            f"4. Explain what was wrong and what you fixed\n\n"
            f"Use tools to read files, understand context, and make edits."
        )

        await self._stream_to_console(ctx, prompt, use_tools=True)
