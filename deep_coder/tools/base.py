"""Tool base class, registry, and OpenAI function schema generation."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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


class ToolRegistry:
    """Registry that holds all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

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
            return await tool.execute(**kwargs)
        except json.JSONDecodeError as e:
            return ToolResult.error(f"Invalid JSON arguments: {e}")
        except TypeError as e:
            return ToolResult.error(f"Invalid arguments for tool '{name}': {e}")
        except Exception as e:
            return ToolResult.error(f"Tool execution failed: {e}")


def create_default_registry() -> ToolRegistry:
    from deep_coder.tools.file_ops import (
        EditFileTool,
        ListFilesTool,
        ReadFileTool,
        WriteFileTool,
    )
    from deep_coder.tools.search import GlobFilesTool, GrepFilesTool
    from deep_coder.tools.shell import ExecShellTool

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(ListFilesTool())
    registry.register(GrepFilesTool())
    registry.register(GlobFilesTool())
    registry.register(ExecShellTool())
    return registry
