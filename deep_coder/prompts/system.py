"""System prompt loading and template management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).parent

MAX_CODER_MD_CHARS = 10000
MAX_MEMORY_CHARS = 10000

_UNSET = object()


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def _find_coder_md(cwd: str | None) -> str | None:
    """Search for CODER.md in cwd and ancestor directories (up to git root)."""
    if not cwd:
        return None
    current = Path(cwd)
    for parent in [current, *current.parents]:
        candidate = parent / "CODER.md"
        if candidate.is_file():
            try:
                content = candidate.read_text(encoding="utf-8", errors="replace")
                if len(content) > MAX_CODER_MD_CHARS:
                    content = content[:MAX_CODER_MD_CHARS] + "\n\n... (truncated)"
                return content
            except OSError:
                return None
        if (parent / ".git").exists():
            break
    return None


def _load_memories(cwd: str | None) -> str | None:
    from deep_coder.memory import MemoryStore
    store = MemoryStore(cwd=cwd)
    return store.get_prompt_section(max_chars=MAX_MEMORY_CHARS)


def get_orchestrator_prompt(
    cwd: str | None = None,
    project_context: Any = None,
    *,
    cached_coder_md: Any = _UNSET,
    cached_memories: Any = _UNSET,
) -> str:
    base = load_prompt("orchestrator")
    context_parts = [base]
    cm = cached_coder_md if cached_coder_md is not _UNSET else _find_coder_md(cwd)
    if cm:
        context_parts.append(f"\n## Project Context (CODER.md)\n{cm}")
    mem = cached_memories if cached_memories is not _UNSET else _load_memories(cwd)
    if mem:
        context_parts.append(f"\n## User Memories\n{mem}")
    if cwd:
        context_parts.append(f"\n## Current Working Directory\n{cwd}")
    if project_context:
        context_parts.append(
            f"\n## Project Status\n{project_context.format_for_prompt()}"
        )
    return "\n".join(context_parts)


def get_worker_prompt(
    task_description: str,
    task_context: str = "",
    cwd: str | None = None,
    conversation_summary: str = "",
    *,
    cached_coder_md: Any = _UNSET,
    cached_memories: Any = _UNSET,
) -> str:
    base = load_prompt("worker")
    parts = [base]
    cm = cached_coder_md if cached_coder_md is not _UNSET else _find_coder_md(cwd)
    if cm:
        parts.append(f"\n## Project Context (CODER.md)\n{cm}")
    mem = cached_memories if cached_memories is not _UNSET else _load_memories(cwd)
    if mem:
        parts.append(f"\n## User Memories\n{mem}")
    if conversation_summary:
        parts.append(f"\n## Conversation Context\n{conversation_summary}")
    parts.append(f"\n## Your Assigned Task\n{task_description}")
    if task_context:
        parts.append(f"\n## Additional Context\n{task_context}")
    return "\n".join(parts)
