"""Project context collection — git state and directory structure for planning."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".venv", "venv", ".env",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".eggs", "*.egg-info",
    ".idea", ".vscode", ".cursor",
})

_MAX_STATUS_LINES = 100
_MAX_TREE_LINES = 200
_MAX_COMMITS = 15


@dataclass
class ProjectContext:
    git_branch: str
    git_status: str
    git_recent_commits: str
    directory_tree: str
    is_git_repo: bool

    def format_for_prompt(self) -> str:
        parts: list[str] = []
        if self.is_git_repo:
            parts.append(f"Branch: {self.git_branch}")
            if self.git_status:
                parts.append(f"Status:\n{self.git_status}")
            else:
                parts.append("Status: (clean)")
            if self.git_recent_commits:
                parts.append(f"\nRecent commits:\n{self.git_recent_commits}")
        if self.directory_tree:
            parts.append(f"\nProject structure:\n{self.directory_tree}")
        return "\n".join(parts)


async def _run_git(cwd: str, *args: str) -> tuple[int, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace").strip()
    except (asyncio.TimeoutError, FileNotFoundError, OSError):
        return 1, ""


def _build_directory_tree(cwd: str, max_depth: int = 3) -> str:
    root = Path(cwd)
    lines: list[str] = []

    def _walk(path: Path, prefix: str, depth: int) -> None:
        if len(lines) >= _MAX_TREE_LINES:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return
        dirs = [e for e in entries if e.is_dir() and e.name not in _SKIP_DIRS]
        files = [e for e in entries if e.is_file() and not e.name.startswith(".")]
        for f in files:
            if len(lines) >= _MAX_TREE_LINES:
                lines.append(f"{prefix}...")
                return
            lines.append(f"{prefix}{f.name}")
        for d in dirs:
            if len(lines) >= _MAX_TREE_LINES:
                lines.append(f"{prefix}...")
                return
            lines.append(f"{prefix}{d.name}/")
            if depth < max_depth:
                _walk(d, prefix + "  ", depth + 1)

    _walk(root, "", 1)
    return "\n".join(lines)


def _truncate_lines(text: str, max_lines: int) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more)"


async def collect_project_context(cwd: str | None) -> ProjectContext | None:
    if not cwd:
        return None

    check_code, _ = await _run_git(cwd, "rev-parse", "--is-inside-work-tree")
    is_git = check_code == 0

    git_branch = ""
    git_status = ""
    git_commits = ""

    if is_git:
        results = await asyncio.gather(
            _run_git(cwd, "rev-parse", "--abbrev-ref", "HEAD"),
            _run_git(cwd, "status", "--short"),
            _run_git(cwd, "log", "--oneline", f"-{_MAX_COMMITS}"),
        )
        _, git_branch = results[0]
        code_s, raw_status = results[1]
        if code_s == 0 and raw_status:
            git_status = _truncate_lines(raw_status, _MAX_STATUS_LINES)
        code_l, raw_log = results[2]
        if code_l == 0 and raw_log:
            git_commits = raw_log

    tree = _build_directory_tree(cwd)

    return ProjectContext(
        git_branch=git_branch or "(unknown)",
        git_status=git_status,
        git_recent_commits=git_commits,
        directory_tree=tree,
        is_git_repo=is_git,
    )
