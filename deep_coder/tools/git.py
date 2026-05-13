"""Git integration tools."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from deep_coder.tools.base import Tool, ToolResult


class _GitBaseTool(Tool):
    """Base for git tools — all run git commands under the hood."""

    async def _run_git(self, *args: str, cwd: str | None = None) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or os.getcwd(),
        )
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )


class GitStatusTool(_GitBaseTool):
    @property
    def name(self) -> str:
        return "git_status"

    @property
    def description(self) -> str:
        return "Show the working tree status (staged, unstaged, untracked files)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, **_: Any) -> ToolResult:
        code, out, err = await self._run_git("status", "--short")
        if code != 0:
            return ToolResult.error(f"git status failed: {err}")
        return ToolResult.ok(out or "(clean working tree)")


class GitDiffTool(_GitBaseTool):
    @property
    def name(self) -> str:
        return "git_diff"

    @property
    def description(self) -> str:
        return "Show changes between working tree and index (unstaged changes), or between commits."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes (--cached). Default: false.",
                },
                "ref": {
                    "type": "string",
                    "description": "Compare against a ref (e.g., 'main', 'HEAD~3').",
                },
            },
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, staged: bool = False, ref: str | None = None, **_: Any) -> ToolResult:
        args = ["diff"]
        if staged:
            args.append("--cached")
        if ref:
            args.append(ref)
        code, out, err = await self._run_git(*args)
        if code != 0:
            return ToolResult.error(f"git diff failed: {err}")
        return ToolResult.ok(out or "(no differences)")


class GitLogTool(_GitBaseTool):
    @property
    def name(self) -> str:
        return "git_log"

    @property
    def description(self) -> str:
        return "Show recent commit history."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of commits to show. Default: 10.",
                },
                "oneline": {
                    "type": "boolean",
                    "description": "Use one-line format. Default: true.",
                },
            },
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, count: int = 10, oneline: bool = True, **_: Any) -> ToolResult:
        args = ["log", f"-{count}"]
        if oneline:
            args.append("--oneline")
        code, out, err = await self._run_git(*args)
        if code != 0:
            return ToolResult.error(f"git log failed: {err}")
        return ToolResult.ok(out or "(no commits)")


class GitBranchTool(_GitBaseTool):
    @property
    def name(self) -> str:
        return "git_branch"

    @property
    def description(self) -> str:
        return "List, create, or delete git branches."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "create": {
                    "type": "string",
                    "description": "Name of a new branch to create (from current HEAD).",
                },
                "delete": {
                    "type": "string",
                    "description": "Name of a branch to delete.",
                },
            },
        }

    @property
    def requires_approval(self) -> bool:
        return True

    async def execute(
        self,
        create: str | None = None,
        delete: str | None = None,
        **_: Any,
    ) -> ToolResult:
        if create:
            code, out, err = await self._run_git("checkout", "-b", create)
            if code != 0:
                return ToolResult.error(f"git checkout -b failed: {err}")
            return ToolResult.ok(f"Created and switched to branch '{create}'")
        if delete:
            code, out, err = await self._run_git("branch", "-d", delete)
            if code != 0:
                return ToolResult.error(f"git branch -d failed: {err}")
            return ToolResult.ok(out)
        code, out, err = await self._run_git("branch", "-a")
        if code != 0:
            return ToolResult.error(f"git branch failed: {err}")
        return ToolResult.ok(out or "(no branches)")


class GitCheckoutTool(_GitBaseTool):
    @property
    def name(self) -> str:
        return "git_checkout"

    @property
    def description(self) -> str:
        return "Switch to an existing branch or restore files."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "Branch name to switch to.",
                },
            },
            "required": ["branch"],
        }

    @property
    def requires_approval(self) -> bool:
        return True

    async def execute(self, branch: str, **_: Any) -> ToolResult:
        code, out, err = await self._run_git("checkout", branch)
        if code != 0:
            return ToolResult.error(f"git checkout failed: {err}")
        return ToolResult.ok(f"Switched to branch '{branch}'")


class GitCommitTool(_GitBaseTool):
    @property
    def name(self) -> str:
        return "git_commit"

    @property
    def description(self) -> str:
        return (
            "Stage files and create a git commit. "
            "Specify files to stage, or use all=true to stage all changes."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message.",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files to stage. Ignored if all=true.",
                },
                "all": {
                    "type": "boolean",
                    "description": "Stage all tracked changes (git add -A). Default: false.",
                },
            },
            "required": ["message"],
        }

    async def execute(
        self,
        message: str,
        files: list[str] | None = None,
        all: bool = False,
        **_: Any,
    ) -> ToolResult:
        if all:
            code, _, err = await self._run_git("add", "-A")
        elif files:
            code, _, err = await self._run_git("add", *files)
        else:
            return ToolResult.error("Specify files to stage or use all=true.")
        if code != 0:
            return ToolResult.error(f"git add failed: {err}")

        code, out, err = await self._run_git("commit", "-m", message)
        if code != 0:
            return ToolResult.error(f"git commit failed: {err}")
        return ToolResult.ok(out)
