"""Tool base class, registry, snapshot tracker, and OpenAI function schema generation."""

from __future__ import annotations

import json
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ToolResult:
    content: str
    success: bool = True
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def ok(cls, content: str, **metadata: Any) -> ToolResult:
        return cls(content=content, success=True, metadata=metadata or None)

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(content=message, success=False)


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]: ...

    @property
    def is_read_only(self) -> bool:
        return False

    @property
    def requires_approval(self) -> bool:
        return not self.is_read_only

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class FileSnapshot:
    """Records a file's state before modification for undo support."""
    file_path: str
    original_content: Optional[str]
    existed: bool


class SnapshotTracker:
    """Tracks file modifications for /diff and /undo."""

    def __init__(self) -> None:
        self._snapshots: list[FileSnapshot] = []
        self._modified_files: dict[str, str | None] = {}

    def capture(self, file_path: str) -> None:
        path = Path(file_path).expanduser().resolve()
        key = str(path)
        if key in self._modified_files:
            return
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8", errors="replace")
            self._snapshots.append(FileSnapshot(key, content, True))
            self._modified_files[key] = content
        else:
            self._snapshots.append(FileSnapshot(key, None, False))
            self._modified_files[key] = None

    def undo_last(self) -> Optional[str]:
        if not self._snapshots:
            return None
        snap = self._snapshots.pop()
        path = Path(snap.file_path)
        if snap.existed and snap.original_content is not None:
            path.write_text(snap.original_content, encoding="utf-8")
        elif not snap.existed and path.exists():
            path.unlink()
        self._modified_files.pop(snap.file_path, None)
        return snap.file_path

    def get_diffs(self) -> list[tuple[str, str | None, str | None]]:
        """Returns list of (path, original, current) for modified files."""
        results = []
        for fpath, original in self._modified_files.items():
            path = Path(fpath)
            current = path.read_text(encoding="utf-8", errors="replace") if path.exists() else None
            if original != current:
                results.append((fpath, original, current))
        return results

    def clear(self) -> None:
        self._snapshots.clear()
        self._modified_files.clear()

    @property
    def has_changes(self) -> bool:
        return any(
            (Path(fp).read_text(encoding="utf-8", errors="replace") if Path(fp).exists() else None) != orig
            for fp, orig in self._modified_files.items()
        )


class ToolRegistry:
    """Registry that holds all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self.snapshots = SnapshotTracker()

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def dispatch(self, name: str, arguments: str) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult.error(f"Tool not found: {name}")
        try:
            kwargs = json.loads(arguments) if arguments else {}
            old_content: str | None = None
            resolved_path: str | None = None
            if not tool.is_read_only:
                file_path = kwargs.get("file_path") or kwargs.get("path")
                if file_path:
                    self.snapshots.capture(file_path)
                    resolved_path = str(Path(file_path).expanduser().resolve())
                    old_content = self._modified_files_get(resolved_path)
            result = await tool.execute(**kwargs)
            if resolved_path and result.success and not tool.is_read_only:
                p = Path(resolved_path)
                new_content = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["file_path"] = resolved_path
                result.metadata["old_content"] = old_content
                result.metadata["new_content"] = new_content
            return result
        except json.JSONDecodeError as e:
            return ToolResult.error(f"Invalid JSON arguments: {e}")
        except TypeError as e:
            return ToolResult.error(f"Invalid arguments for tool '{name}': {e}")
        except Exception as e:
            return ToolResult.error(f"Tool execution failed: {e}")

    def _modified_files_get(self, resolved_path: str) -> str | None:
        return self.snapshots._modified_files.get(resolved_path)


def create_default_registry() -> ToolRegistry:
    from deep_coder.tools.file_ops import (
        DeleteFileTool,
        EditFileTool,
        InsertTextTool,
        ListFilesTool,
        MoveFileTool,
        MultiEditFileTool,
        ReadFileTool,
        WriteFileTool,
    )
    from deep_coder.tools.git import (
        GitBranchTool,
        GitCheckoutTool,
        GitCommitTool,
        GitDiffTool,
        GitLogTool,
        GitStatusTool,
    )
    from deep_coder.tools.search import GlobFilesTool, GrepFilesTool
    from deep_coder.tools.shell import ExecShellTool

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(MultiEditFileTool())
    registry.register(InsertTextTool())
    registry.register(DeleteFileTool())
    registry.register(MoveFileTool())
    registry.register(ListFilesTool())
    registry.register(GrepFilesTool())
    registry.register(GlobFilesTool())
    registry.register(ExecShellTool())
    registry.register(GitStatusTool())
    registry.register(GitDiffTool())
    registry.register(GitLogTool())
    registry.register(GitCommitTool())
    registry.register(GitBranchTool())
    registry.register(GitCheckoutTool())
    return registry
