"""Extended deep reasoning mode for complex questions."""

from __future__ import annotations

from deep_coder.display import print_error, print_info
from deep_coder.skills.base import Skill, SkillContext


class ThinkSkill(Skill):
    @property
    def name(self) -> str:
        return "/think"

    @property
    def description(self) -> str:
        return "Deep reasoning mode for architecture and design questions"

    @property
    def usage(self) -> str:
        return "/think <question>"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        question = arg.strip()
        if not question:
            print_error("Provide a question. Usage: /think <question>")
            return

        print_info("Thinking deeply...")

        prompt = (
            f"## Deep Analysis Request\n\n"
            f"Think step-by-step about the following question. Consider multiple "
            f"angles, tradeoffs, and edge cases before reaching a conclusion.\n\n"
            f"Question: {question}\n\n"
            f"Structure your response as:\n"
            f"1. **Understanding** — Restate the core problem\n"
            f"2. **Options** — List viable approaches with pros/cons\n"
            f"3. **Analysis** — Deep dive into each option\n"
            f"4. **Recommendation** — Your recommended approach with rationale\n"
            f"5. **Risks** — What could go wrong and how to mitigate\n\n"
            f"Be thorough but practical. Aim for actionable conclusions."
        )

        await self._stream_to_console(ctx, prompt)
