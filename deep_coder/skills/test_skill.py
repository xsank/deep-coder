"""Auto-detect and run tests, analyze failures."""

from __future__ import annotations

from pathlib import Path

from deep_coder.display import print_error, print_info, print_success, print_warning
from deep_coder.skills.base import Skill, SkillContext


class TestSkill(Skill):
    @property
    def name(self) -> str:
        return "/test"

    @property
    def description(self) -> str:
        return "Run tests (auto-detect framework) and analyze failures"

    @property
    def usage(self) -> str:
        return "/test [command]"

    def _detect_test_command(self, cwd: str) -> str | None:
        root = Path(cwd)
        if (root / "pyproject.toml").exists() or (root / "setup.py").exists() or (root / "pytest.ini").exists():
            return "python -m pytest -v"
        if (root / "package.json").exists():
            return "npm test"
        if (root / "go.mod").exists():
            return "go test ./..."
        if (root / "Cargo.toml").exists():
            return "cargo test"
        if (root / "Makefile").exists():
            return "make test"
        return None

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        cmd = arg.strip()
        if not cmd:
            cmd = self._detect_test_command(ctx.cwd)
            if not cmd:
                print_error(
                    "Could not detect test framework. "
                    "Use `/test <command>` to specify a test command."
                )
                return
            print_info(f"Detected test command: {cmd}")

        print_info(f"Running: {cmd}")
        code, stdout, stderr = await self._run_shell(cmd, cwd=ctx.cwd, timeout=300)
        output = (stdout + "\n" + stderr).strip()

        if code == 0:
            print_success("All tests passed!")
            if output:
                from deep_coder.display import console
                console.print(f"\n[dim]{output[-2000:]}[/dim]\n")
            return

        print_warning(f"Tests failed (exit code {code}). Analyzing failures...")
        from deep_coder.display import console
        console.print(f"\n[dim]{output[-3000:]}[/dim]\n")

        prompt = (
            f"## Test Failure Analysis\n\n"
            f"Test command: `{cmd}`\n"
            f"Exit code: {code}\n\n"
            f"```\n{output[-6000:]}\n```\n\n"
            f"Analyze the test failures:\n"
            f"1. Which tests failed and why?\n"
            f"2. What is the root cause?\n"
            f"3. Suggest specific fixes with code snippets\n"
            f"Be concise and actionable."
        )

        await self._stream_to_console(ctx, prompt)
