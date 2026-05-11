"""File operation tools: read, write, edit, list files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from deep_coder.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Returns the file content with line numbers."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to read.",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-based). Default: 0.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read. Default: 2000.",
                },
            },
            "required": ["file_path"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, file_path: str, offset: int = 0, limit: int = 2000, **_: Any) -> ToolResult:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return ToolResult.error(f"File not found: {path}")
        if not path.is_file():
            return ToolResult.error(f"Not a file: {path}")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total = len(lines)
            selected = lines[offset : offset + limit]
            numbered = [f"{i + offset + 1}\t{line}" for i, line in enumerate(selected)]
            result = "\n".join(numbered)
            if offset + limit < total:
                result += f"\n... ({total - offset - limit} more lines)"
            return ToolResult.ok(result, total_lines=total)
        except Exception as e:
            return ToolResult.error(f"Failed to read file: {e}")


class WriteFileTool(Tool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Create or overwrite a file with the given content."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, file_path: str, content: str, **_: Any) -> ToolResult:
        path = Path(file_path).expanduser().resolve()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return ToolResult.ok(f"Written {lines} lines to {path}")
        except Exception as e:
            return ToolResult.error(f"Failed to write file: {e}")


class EditFileTool(Tool):
    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return (
            "Edit a file by replacing an exact string match with new content. "
            "The old_string must match exactly (including whitespace/indentation)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit.",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace.",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement string.",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false).",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **_: Any,
    ) -> ToolResult:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return ToolResult.error(f"File not found: {path}")
        try:
            content = path.read_text(encoding="utf-8")
            count = content.count(old_string)
            if count == 0:
                return ToolResult.error(
                    f"old_string not found in {path}. Make sure the string matches exactly."
                )
            if count > 1 and not replace_all:
                return ToolResult.error(
                    f"old_string found {count} times. Use replace_all=true or provide more context."
                )
            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
            path.write_text(new_content, encoding="utf-8")
            return ToolResult.ok(f"Replaced {count if replace_all else 1} occurrence(s) in {path}")
        except Exception as e:
            return ToolResult.error(f"Failed to edit file: {e}")


class ListFilesTool(Tool):
    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in a directory, optionally with a glob pattern."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Default: current directory.",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '**/*.py'). Default: '*'.",
                },
            },
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, path: str = ".", pattern: str = "*", **_: Any) -> ToolResult:
        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists():
            return ToolResult.error(f"Directory not found: {dir_path}")
        if not dir_path.is_dir():
            return ToolResult.error(f"Not a directory: {dir_path}")
        try:
            files = sorted(dir_path.glob(pattern))
            entries = []
            for f in files[:500]:
                rel = f.relative_to(dir_path)
                prefix = "d " if f.is_dir() else "f "
                entries.append(f"{prefix}{rel}")
            result = "\n".join(entries) if entries else "(empty)"
            if len(files) > 500:
                result += f"\n... ({len(files) - 500} more entries)"
            return ToolResult.ok(result, total=len(files))
        except Exception as e:
            return ToolResult.error(f"Failed to list files: {e}")
