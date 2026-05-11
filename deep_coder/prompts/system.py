"""System prompt loading and template management."""

from __future__ import annotations

import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def get_orchestrator_prompt(cwd: str | None = None) -> str:
    base = load_prompt("orchestrator")
    context_parts = [base]
    if cwd:
        context_parts.append(f"\n## Current Working Directory\n{cwd}")
    return "\n".join(context_parts)


def get_worker_prompt(task_description: str, task_context: str = "") -> str:
    base = load_prompt("worker")
    parts = [base, f"\n## Your Assigned Task\n{task_description}"]
    if task_context:
        parts.append(f"\n## Additional Context\n{task_context}")
    return "\n".join(parts)
