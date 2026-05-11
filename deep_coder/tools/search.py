"""Search tools: grep and glob."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from deep_coder.tools.base import Tool, ToolResult

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".o", ".a",
    ".pyc", ".pyo", ".whl", ".egg",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".sqlite", ".db", ".bin",
}


class GrepFilesTool(Tool):
    @property
    def name(self) -> str:
        return "grep_files"

    @property
    def description(self) -> str:
        return (
            "Search file contents using a regex pattern. "
            "Returns matching lines with file paths and line numbers."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in. Default: current directory.",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.py'). Default: all files.",
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Case-insensitive search. Default: false.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matching lines. Default: 200.",
                },
            },
            "required": ["pattern"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        glob: str | None = None,
        case_insensitive: bool = False,
        max_results: int = 200,
        **_: Any,
    ) -> ToolResult:
        search_path = Path(path).expanduser().resolve()
        if not search_path.exists():
            return ToolResult.error(f"Path not found: {search_path}")

        flags = re.IGNORECASE if case_insensitive else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult.error(f"Invalid regex pattern: {e}")

        matches: list[str] = []
        files_searched = 0

        if search_path.is_file():
            file_list = [search_path]
        else:
            file_list = sorted(search_path.rglob(glob or "*"))

        for file_path in file_list:
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() in BINARY_EXTENSIONS:
                continue
            if any(part.startswith(".") for part in file_path.parts):
                continue

            files_searched += 1
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        rel = file_path.relative_to(search_path) if search_path.is_dir() else file_path.name
                        matches.append(f"{rel}:{lineno}: {line.rstrip()}")
                        if len(matches) >= max_results:
                            break
            except (PermissionError, OSError):
                continue

            if len(matches) >= max_results:
                break

        if not matches:
            return ToolResult.ok(f"No matches found ({files_searched} files searched)")

        result = "\n".join(matches)
        if len(matches) >= max_results:
            result += f"\n... (truncated at {max_results} results)"
        return ToolResult.ok(result, files_searched=files_searched, match_count=len(matches))


class GlobFilesTool(Tool):
    @property
    def name(self) -> str:
        return "glob_files"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern. Returns file paths sorted by modification time."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g., '**/*.py', 'src/**/*.ts').",
                },
                "path": {
                    "type": "string",
                    "description": "Base directory to search from. Default: current directory.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results. Default: 200.",
                },
            },
            "required": ["pattern"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        max_results: int = 200,
        **_: Any,
    ) -> ToolResult:
        base = Path(path).expanduser().resolve()
        if not base.exists():
            return ToolResult.error(f"Path not found: {base}")

        try:
            files = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            files = [f for f in files if f.is_file()]
            total = len(files)
            truncated = files[:max_results]
            entries = [str(f.relative_to(base)) for f in truncated]
            result = "\n".join(entries) if entries else "(no matches)"
            if total > max_results:
                result += f"\n... ({total - max_results} more files)"
            return ToolResult.ok(result, total=total)
        except Exception as e:
            return ToolResult.error(f"Glob search failed: {e}")
