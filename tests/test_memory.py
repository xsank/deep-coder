"""Tests for the memory storage module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from deep_coder.memory import Memory, MemoryStore, MemoryType


class TestMemoryType:
    def test_enum_values(self):
        assert MemoryType.USER == "user"
        assert MemoryType.FEEDBACK == "feedback"
        assert MemoryType.PROJECT == "project"
        assert MemoryType.REFERENCE == "reference"


class TestSlugify:
    def test_basic(self):
        assert MemoryStore.slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert MemoryStore.slugify("file/path@name!") == "file-path-name"

    def test_max_length(self):
        slug = MemoryStore.slugify("a" * 100)
        assert len(slug) <= 64

    def test_empty_string(self):
        assert MemoryStore.slugify("") == "memory"

    def test_chinese_chars(self):
        slug = MemoryStore.slugify("测试记忆")
        assert "测试记忆" in slug


class TestMemoryStore:
    def _make_store(self, tmp_dir: str) -> MemoryStore:
        store = MemoryStore(cwd=tmp_dir)
        store._local_dir = Path(tmp_dir) / "memory"
        store._global_dir = Path(tmp_dir) / "global_memory"
        return store

    def _make_memory(self, id: str = "test-mem", **kwargs) -> Memory:
        defaults = {
            "id": id,
            "type": MemoryType.FEEDBACK,
            "name": "Test Memory",
            "description": "A test memory",
            "content": "This is test content.",
        }
        defaults.update(kwargs)
        return Memory(**defaults)

    def test_save_and_get(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            mem = self._make_memory()
            path = store.save(mem)
            assert path.exists()
            retrieved = store.get("test-mem")
            assert retrieved is not None
            assert retrieved.name == "Test Memory"
            assert retrieved.content == "This is test content."
            assert retrieved.type == MemoryType.FEEDBACK

    def test_get_nonexistent(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            assert store.get("nonexistent") is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            mem = self._make_memory()
            store.save(mem)
            assert store.delete("test-mem") is True
            assert store.get("test-mem") is None

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            assert store.delete("nonexistent") is False

    def test_list_all(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", name="First"))
            store.save(self._make_memory("m2", name="Second", type=MemoryType.USER))
            all_mems = store.list_all()
            assert len(all_mems) == 2

    def test_list_all_with_filter(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", type=MemoryType.FEEDBACK))
            store.save(self._make_memory("m2", type=MemoryType.USER))
            feedback = store.list_all(type_filter=MemoryType.FEEDBACK)
            assert len(feedback) == 1
            assert feedback[0].type == MemoryType.FEEDBACK

    def test_search(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", name="Python tips", content="use type hints"))
            store.save(self._make_memory("m2", name="Go notes", content="use interfaces"))
            results = store.search("python")
            assert len(results) == 1
            assert results[0].id == "m1"

    def test_search_case_insensitive(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", content="IMPORTANT note"))
            results = store.search("important")
            assert len(results) == 1

    def test_get_prompt_section(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", name="Rule", content="Always lint"))
            section = store.get_prompt_section()
            assert section is not None
            assert "Rule" in section
            assert "Always lint" in section

    def test_get_prompt_section_empty(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            assert store.get_prompt_section() is None

    def test_get_prompt_section_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", content="x" * 500))
            store.save(self._make_memory("m2", content="y" * 500))
            section = store.get_prompt_section(max_chars=100)
            assert section is not None
            assert len(section) <= 150

    def test_rebuild_index(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            store.save(self._make_memory("m1", name="First"))
            index = Path(d) / "memory" / "MEMORY.md"
            assert index.exists()
            content = index.read_text()
            assert "First" in content

    def test_memory_frontmatter_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._make_store(d)
            mem = Memory(
                id="roundtrip",
                type=MemoryType.PROJECT,
                name="Project Note",
                description="desc here",
                content="Multi\nline\ncontent",
                created="2025-01-01",
            )
            store.save(mem)
            retrieved = store.get("roundtrip")
            assert retrieved is not None
            assert retrieved.type == MemoryType.PROJECT
            assert retrieved.name == "Project Note"
            assert retrieved.description == "desc here"
            assert "Multi\nline\ncontent" in retrieved.content
