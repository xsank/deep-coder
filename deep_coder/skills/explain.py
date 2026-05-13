"""Explain code in context."""

from __future__ import annotations

from pathlib import Path

from deep_coder.display import print_error, print_info
from deep_coder.skills.base import Skill, SkillContext


class ExplainSkill(Skill):
    @property
    def name(self) -> str:
        return "/explain"

    @property
    def description(self) -> str:
        return "Explain a file, function, or code section"

    @property
    def usage(self) -> str:
        return "/explain [file[:line[-line]]]"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        target = arg.strip()

        if not target:
            print_info("Explaining project overview...")
            coder_md = Path(ctx.cwd) / "CODER.md"
            if coder_md.exists():
                content = coder_md.read_text(encoding="utf-8", errors="replace")
                prompt = (
                    f"Explain this project based on its CODER.md documentation:\n\n"
                    f"```markdown\n{content}\n```\n\n"
                    f"Provide a clear overview: what it does, how it's structured, "
                    f"and how the key components work together."
                )
            else:
                prompt = (
                    f"The user wants an overview of the project in directory: {ctx.cwd}\n\n"
                    f"Read key files (README, setup files, main source) to understand "
                    f"the project, then explain: what it does, tech stack, architecture, "
                    f"and how the main components work together."
                )
                await self._stream_to_console(ctx, prompt, use_tools=True)
                return

            await self._stream_to_console(ctx, prompt)
            return

        file_part = target
        start_line = None
        end_line = None

        if ":" in target:
            file_part, line_spec = target.rsplit(":", 1)
            if "-" in line_spec:
                parts = line_spec.split("-", 1)
                try:
                    start_line = int(parts[0])
                    end_line = int(parts[1])
                except ValueError:
                    print_error(f"Invalid line range: {line_spec}")
                    return
            else:
                try:
                    start_line = int(line_spec)
                    end_line = start_line + 30
                except ValueError:
                    print_error(f"Invalid line number: {line_spec}")
                    return

        file_path = Path(ctx.cwd) / file_part
        if not file_path.exists():
            print_error(f"File not found: {file_part}")
            return

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        if start_line is not None:
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line) if end_line else min(len(lines), start_idx + 30)
            numbered = "\n".join(
                f"{i + start_idx + 1:4d} | {line}"
                for i, line in enumerate(lines[start_idx:end_idx])
            )
            location = f"{file_part}:{start_line}-{end_idx}"
            print_info(f"Explaining {location}...")
        else:
            if len(lines) > 200:
                numbered = "\n".join(f"{i + 1:4d} | {line}" for i, line in enumerate(lines[:200]))
                numbered += f"\n... ({len(lines) - 200} more lines)"
            else:
                numbered = "\n".join(f"{i + 1:4d} | {line}" for i, line in enumerate(lines))
            location = file_part
            print_info(f"Explaining {location}...")

        suffix = file_path.suffix
        prompt = (
            f"## Code Explanation Request\n\n"
            f"File: `{location}`\n\n"
            f"```{suffix.lstrip('.')}\n{numbered}\n```\n\n"
            f"Explain this code clearly:\n"
            f"1. **Purpose** — What does this code do and why?\n"
            f"2. **How it works** — Walk through the key logic\n"
            f"3. **Key details** — Important patterns, algorithms, or non-obvious behavior\n"
            f"4. **Dependencies** — What it relies on and what relies on it\n\n"
            f"Be concise. Focus on what a developer needs to understand to work with this code."
        )

        await self._stream_to_console(ctx, prompt)
