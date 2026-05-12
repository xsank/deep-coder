"""File operation tools: read, write, edit, list, delete, move, multi-edit, insert."""

from __future__ import annotations

import shutil
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


class DeleteFileTool(Tool):
    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return "Delete a file or empty directory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file or empty directory to delete.",
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, file_path: str, **_: Any) -> ToolResult:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return ToolResult.error(f"Path not found: {path}")
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
                return ToolResult.ok(f"Deleted file: {path}")
            elif path.is_dir():
                path.rmdir()
                return ToolResult.ok(f"Deleted empty directory: {path}")
            else:
                return ToolResult.error(f"Cannot delete: {path}")
        except OSError as e:
            return ToolResult.error(f"Failed to delete: {e}")


class MoveFileTool(Tool):
    @property
    def name(self) -> str:
        return "move_file"

    @property
    def description(self) -> str:
        return "Move or rename a file or directory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Path to the source file or directory.",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path (new name or directory).",
                },
            },
            "required": ["source", "destination"],
        }

    async def execute(
        self, source: str, destination: str, **_: Any,
    ) -> ToolResult:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()
        if not src.exists():
            return ToolResult.error(f"Source not found: {src}")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return ToolResult.ok(f"Moved {src} → {dst}")
        except Exception as e:
            return ToolResult.error(f"Failed to move: {e}")


class MultiEditFileTool(Tool):
    @property
    def name(self) -> str:
        return "multi_edit_file"

    @property
    def description(self) -> str:
        return (
            "Apply multiple find-and-replace edits to a single file in one call. "
            "Each edit replaces an exact string match. All edits are atomic — "
            "if any old_string is not found, no changes are applied."
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
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "old_string": {
                                "type": "string",
                                "description": "Exact string to find.",
                            },
                            "new_string": {
                                "type": "string",
                                "description": "Replacement string.",
                            },
                        },
                        "required": ["old_string", "new_string"],
                    },
                    "description": "List of edits to apply sequentially.",
                },
            },
            "required": ["file_path", "edits"],
        }

    async def execute(
        self,
        file_path: str,
        edits: list[dict[str, str]],
        **_: Any,
    ) -> ToolResult:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return ToolResult.error(f"File not found: {path}")
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult.error(f"Failed to read file: {e}")

        missing: list[int] = []
        for i, edit in enumerate(edits):
            old = edit.get("old_string", "")
            if old not in content:
                missing.append(i + 1)

        if missing:
            return ToolResult.error(
                f"old_string not found for edit(s) #{', #'.join(str(n) for n in missing)}. "
                "No changes applied."
            )

        applied = 0
        for edit in edits:
            old = edit["old_string"]
            new = edit["new_string"]
            count = content.count(old)
            if count > 1:
                return ToolResult.error(
                    f"old_string found {count} times (edit #{applied + 1}). "
                    "Provide more context to make it unique. No changes applied."
                )
            content = content.replace(old, new, 1)
            applied += 1

        try:
            path.write_text(content, encoding="utf-8")
            return ToolResult.ok(f"Applied {applied} edit(s) to {path}")
        except Exception as e:
            return ToolResult.error(f"Failed to write file: {e}")


class InsertTextTool(Tool):
    @property
    def name(self) -> str:
        return "insert_text"

    @property
    def description(self) -> str:
        return (
            "Insert text at a specific line number in a file. "
            "Line numbers are 1-based. The new content is inserted before the specified line."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file.",
                },
                "line": {
                    "type": "integer",
                    "description": "Line number to insert before (1-based). "
                    "Use a value beyond the last line to append.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to insert.",
                },
            },
            "required": ["file_path", "line", "content"],
        }

    async def execute(
        self, file_path: str, line: int, content: str, **_: Any,
    ) -> ToolResult:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return ToolResult.error(f"File not found: {path}")
        try:
            existing = path.read_text(encoding="utf-8")
            lines = existing.splitlines(keepends=True)
            insert_idx = max(0, min(line - 1, len(lines)))
            new_lines = content.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            lines[insert_idx:insert_idx] = new_lines
            path.write_text("".join(lines), encoding="utf-8")
            n = len(new_lines)
            return ToolResult.ok(
                f"Inserted {n} line{'s' if n != 1 else ''} at line {line} in {path}"
            )
        except Exception as e:
            return ToolResult.error(f"Failed to insert text: {e}")
