"""Generate PR title and description from branch diff."""

from __future__ import annotations

from deep_coder.display import print_error, print_info, print_warning
from deep_coder.skills.base import Skill, SkillContext


class PRSkill(Skill):
    @property
    def name(self) -> str:
        return "/pr"

    @property
    def description(self) -> str:
        return "Generate a PR title and description from branch changes"

    @property
    def usage(self) -> str:
        return "/pr [base-branch]"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        base = arg.strip() or "main"

        code, branch, _ = await self._run_git("branch", "--show-current", cwd=ctx.cwd)
        branch = branch.strip()
        if not branch:
            print_error("Not on a git branch.")
            return
        if branch == base:
            print_warning(f"Currently on {base}. Switch to a feature branch first.")
            return

        code, log, _ = await self._run_git("log", f"{base}..HEAD", "--oneline", cwd=ctx.cwd)
        if code != 0 or not log.strip():
            print_warning(f"No commits ahead of {base}.")
            return

        code, diff, _ = await self._run_git("diff", f"{base}...HEAD", "--stat", cwd=ctx.cwd)
        code, full_diff, _ = await self._run_git("diff", f"{base}...HEAD", cwd=ctx.cwd)

        print_info(f"Generating PR description for {branch} → {base}...")

        prompt = (
            f"## PR Description Request\n\n"
            f"Branch: `{branch}` → `{base}`\n\n"
            f"### Commits\n```\n{log}\n```\n\n"
            f"### Changed files\n```\n{diff}\n```\n\n"
            f"### Full diff\n```diff\n{full_diff[:12000]}\n```\n\n"
            f"Generate a pull request with:\n"
            f"1. **Title** — concise, under 72 chars, imperative mood\n"
            f"2. **Summary** — 2-4 bullet points explaining WHAT and WHY\n"
            f"3. **Changes** — key changes organized by area\n"
            f"4. **Test Plan** — how to verify these changes\n\n"
            f"Output in Markdown format ready to paste into GitHub/GitLab."
        )

        await self._stream_to_console(ctx, prompt)
