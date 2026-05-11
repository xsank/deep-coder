"""AI code review skill."""

from __future__ import annotations

from pathlib import Path

from deep_coder.display import print_error, print_info, print_warning
from deep_coder.skills.base import Skill, SkillContext


class ReviewSkill(Skill):
    @property
    def name(self) -> str:
        return "/review"

    @property
    def description(self) -> str:
        return "AI code review for staged changes or a specific file"

    @property
    def usage(self) -> str:
        return "/review [file|staged]"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        arg = arg.strip()

        if arg and arg != "staged":
            file_path = Path(ctx.cwd) / arg
            if not file_path.exists():
                print_error(f"File not found: {arg}")
                return
            content = file_path.read_text(encoding="utf-8", errors="replace")
            print_info(f"Reviewing {arg}...")
            prompt = (
                f"## Code Review Request\n\n"
                f"Review the following file: `{arg}`\n\n"
                f"```\n{content}\n```\n\n"
                f"Provide a structured code review covering:\n"
                f"1. **Bugs** — Logic errors, off-by-one, null/None issues\n"
                f"2. **Security** — Injection, auth, data exposure risks\n"
                f"3. **Error Handling** — Missing try/catch, unhandled edge cases\n"
                f"4. **Performance** — Inefficient patterns, N+1 queries\n"
                f"5. **Style** — Naming, structure, readability improvements\n\n"
                f"For each finding, specify severity (critical/warning/suggestion) and the exact line(s). "
                f"If the code looks good, say so."
            )
        else:
            code, staged_diff, _ = await self._run_git("diff", "--cached", cwd=ctx.cwd)
            if not staged_diff.strip():
                code, unstaged_diff, _ = await self._run_git("diff", cwd=ctx.cwd)
                if not unstaged_diff.strip():
                    print_warning("No staged or unstaged changes to review.")
                    return
                print_info("No staged changes. Reviewing unstaged changes...")
                diff = unstaged_diff
            else:
                print_info("Reviewing staged changes...")
                diff = staged_diff

            prompt = (
                f"## Code Review Request\n\n"
                f"Review the following git diff:\n\n"
                f"```diff\n{diff}\n```\n\n"
                f"Provide a structured code review covering:\n"
                f"1. **Bugs** — Logic errors, off-by-one, null/None issues\n"
                f"2. **Security** — Injection, auth, data exposure risks\n"
                f"3. **Error Handling** — Missing try/catch, unhandled edge cases\n"
                f"4. **Performance** — Inefficient patterns, N+1 queries\n"
                f"5. **Style** — Naming, structure, readability improvements\n\n"
                f"For each finding, specify severity (critical/warning/suggestion) "
                f"and the exact location in the diff. If everything looks good, say so."
            )

        await self._stream_to_console(ctx, prompt)
