"""Persistent memory storage — markdown files with YAML frontmatter."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class MemoryType(str, Enum):
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


_TYPE_PRIORITY = {
    MemoryType.FEEDBACK: 0,
    MemoryType.USER: 1,
    MemoryType.PROJECT: 2,
    MemoryType.REFERENCE: 3,
}

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


@dataclass
class Memory:
    id: str
    type: MemoryType
    name: str
    description: str
    content: str
    created: str = field(default_factory=lambda: datetime.date.today().isoformat())
    source: str = "local"


class MemoryStore:
    """File-based memory with global + project-local merging."""

    def __init__(self, cwd: str | None = None) -> None:
        self._global_dir = Path.home() / ".deep-coder" / "memory"
        self._local_dir: Path | None = None
        if cwd:
            root = self._find_project_root(cwd)
            if root:
                self._local_dir = root / ".deep-coder" / "memory"

    @staticmethod
    def _find_project_root(cwd: str) -> Optional[Path]:
        current = Path(cwd)
        for parent in [current, *current.parents]:
            if (parent / ".git").exists() or (parent / ".deep-coder").exists():
                return parent
        return Path(cwd)

    @staticmethod
    def slugify(text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", slug)
        slug = slug.strip("-")
        return slug[:64] or "memory"

    def save(self, memory: Memory, local: bool = True) -> Path:
        directory = self._local_dir if (local and self._local_dir) else self._global_dir
        directory.mkdir(parents=True, exist_ok=True)
        path = self._write_memory_file(memory, directory)
        self._rebuild_index(directory)
        return path

    def delete(self, memory_id: str) -> bool:
        for d in [self._local_dir, self._global_dir]:
            if not d:
                continue
            path = d / f"{memory_id}.md"
            if path.is_file():
                path.unlink()
                self._rebuild_index(d)
                return True
        return False

    def get(self, memory_id: str) -> Optional[Memory]:
        for d in [self._local_dir, self._global_dir]:
            if not d:
                continue
            path = d / f"{memory_id}.md"
            if path.is_file():
                return self._read_memory_file(path)
        return None

    def list_all(self, type_filter: Optional[MemoryType] = None) -> list[Memory]:
        merged: dict[str, Memory] = {}
        for mem in self._list_directory(self._global_dir, "global"):
            merged[mem.id] = mem
        for mem in self._list_directory(self._local_dir, "local"):
            merged[mem.id] = mem
        result = list(merged.values())
        if type_filter:
            result = [m for m in result if m.type == type_filter]
        result.sort(key=lambda m: (_TYPE_PRIORITY.get(m.type, 99), m.created))
        return result

    def search(self, query: str) -> list[Memory]:
        q = query.lower()
        return [
            m
            for m in self.list_all()
            if q in m.name.lower() or q in m.description.lower() or q in m.content.lower()
        ]

    def get_prompt_section(self, max_chars: int = 3000) -> Optional[str]:
        memories = self.list_all()
        if not memories:
            return None
        parts: list[str] = []
        used = 0
        for mem in memories:
            entry = f"**[{mem.type.value}] {mem.name}**: {mem.content}"
            if used + len(entry) > max_chars:
                remaining = max_chars - used - 20
                if remaining > 50:
                    parts.append(entry[:remaining] + "... (truncated)")
                break
            parts.append(entry)
            used += len(entry) + 1
        return "\n".join(parts) if parts else None

    def _rebuild_index(self, directory: Path) -> None:
        if not directory or not directory.is_dir():
            return
        memories = self._list_directory(directory)
        lines = ["# Memories\n"]
        if memories:
            lines.append("| Type | Name | Description |")
            lines.append("|------|------|-------------|")
            for m in memories:
                lines.append(f"| {m.type.value} | {m.name} | {m.description} |")
        else:
            lines.append("No memories saved yet.")
        (directory / "MEMORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _read_memory_file(self, path: Path) -> Optional[Memory]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        match = _FRONTMATTER_RE.match(text)
        if not match:
            return None
        frontmatter, content = match.group(1), match.group(2).strip()
        fields: dict[str, str] = {}
        for fm in _FIELD_RE.finditer(frontmatter):
            fields[fm.group(1)] = fm.group(2).strip()
        try:
            mem_type = MemoryType(fields.get("type", "feedback"))
        except ValueError:
            mem_type = MemoryType.FEEDBACK
        return Memory(
            id=path.stem,
            type=mem_type,
            name=fields.get("name", path.stem),
            description=fields.get("description", ""),
            content=content,
            created=fields.get("created", ""),
        )

    def _write_memory_file(self, memory: Memory, directory: Path) -> Path:
        path = directory / f"{memory.id}.md"
        frontmatter = (
            f"---\n"
            f"type: {memory.type.value}\n"
            f"name: {memory.name}\n"
            f"description: {memory.description}\n"
            f"created: {memory.created}\n"
            f"---\n\n"
        )
        path.write_text(frontmatter + memory.content + "\n", encoding="utf-8")
        return path

    def _list_directory(
        self,
        directory: Optional[Path],
        source: str = "local",
    ) -> list[Memory]:
        if not directory or not directory.is_dir():
            return []
        result: list[Memory] = []
        for path in sorted(directory.glob("*.md")):
            if path.name == "MEMORY.md":
                continue
            mem = self._read_memory_file(path)
            if mem:
                mem.source = source
                result.append(mem)
        return result
