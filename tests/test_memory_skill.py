"""Tests for skills/memory.py — RememberSkill._parse_response and MemorySkill subcommands."""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from deep_coder.memory import Memory, MemoryStore, MemoryType
from deep_coder.skills.base import SkillContext
from deep_coder.skills.memory import MemorySkill, RememberSkill


@pytest.fixture
def cwd():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def ctx(cwd):
    return SkillContext(
        orchestrator=MagicMock(),
        client=MagicMock(),
        config=MagicMock(),
        status_panel=None,
        cwd=cwd,
    )


class TestRememberParseResponse:
    def test_json_response(self):
        skill = RememberSkill()
        content = (
            '```json\n{"type": "user", "name": "Likes Python",'
            ' "description": "User prefers Python",'
            ' "content": "User prefers Python over Java"}\n```'
        )
        result = skill._parse_response(content, "original text")
        assert result["type"] == MemoryType.USER
        assert result["name"] == "Likes Python"
        assert "Python" in result["content"]

    def test_inline_json(self):
        skill = RememberSkill()
        content = (
            '{"type": "feedback", "name": "Short responses",'
            ' "description": "Keep it short",'
            ' "content": "User prefers short responses"}'
        )
        result = skill._parse_response(content, "original")
        assert result["type"] == MemoryType.FEEDBACK

    def test_invalid_json_fallback(self):
        skill = RememberSkill()
        content = "This is not JSON at all"
        result = skill._parse_response(content, "my note here")
        assert result["type"] == MemoryType.FEEDBACK
        assert "my" in result["name"]
        assert result["content"] == "my note here"

    def test_bad_type_fallback(self):
        skill = RememberSkill()
        content = '```json\n{"type": "invalid_type", "name": "Test"}\n```'
        result = skill._parse_response(content, "fallback text")
        assert result["type"] == MemoryType.FEEDBACK

    def test_missing_fields(self):
        skill = RememberSkill()
        content = '```json\n{"type": "project"}\n```'
        result = skill._parse_response(content, "some text about project")
        assert result["type"] == MemoryType.PROJECT
        assert "some text" in result["name"]


class TestMemorySkillList:
    @patch("deep_coder.skills.memory.print_info")
    async def test_list_empty(self, mock_info, ctx):
        skill = MemorySkill()
        await skill.execute("list", ctx)
        mock_info.assert_called()
        assert "no memories" in mock_info.call_args[0][0].lower()

    @patch("deep_coder.skills.memory.print_error")
    async def test_list_invalid_type(self, mock_error, ctx):
        skill = MemorySkill()
        await skill.execute("list invalid_type", ctx)
        mock_error.assert_called()

    async def test_list_with_memories(self, ctx, cwd):
        store = MemoryStore(cwd=cwd)
        mem = Memory(
            id="test-mem",
            type=MemoryType.USER,
            name="Test Memory",
            description="A test memory",
            content="Test content",
        )
        store.save(mem)

        skill = MemorySkill()
        await skill.execute("list", ctx)


class TestMemorySkillSearch:
    @patch("deep_coder.skills.memory.print_error")
    async def test_search_empty_query(self, mock_error, ctx):
        skill = MemorySkill()
        await skill.execute("search", ctx)
        mock_error.assert_called()

    @patch("deep_coder.skills.memory.print_info")
    async def test_search_no_results(self, mock_info, ctx):
        skill = MemorySkill()
        await skill.execute("search nonexistent", ctx)
        mock_info.assert_called()
        assert "no memories" in mock_info.call_args[0][0].lower()


class TestMemorySkillShow:
    @patch("deep_coder.skills.memory.print_error")
    async def test_show_empty_id(self, mock_error, ctx):
        skill = MemorySkill()
        await skill.execute("show", ctx)
        mock_error.assert_called()

    @patch("deep_coder.skills.memory.print_error")
    async def test_show_not_found(self, mock_error, ctx):
        skill = MemorySkill()
        await skill.execute("show nonexistent", ctx)
        mock_error.assert_called()
        assert "not found" in mock_error.call_args[0][0].lower()

    async def test_show_found(self, ctx, cwd):
        store = MemoryStore(cwd=cwd)
        mem = Memory(
            id="test-show",
            type=MemoryType.USER,
            name="Show Test",
            description="Test description",
            content="Full content here",
        )
        store.save(mem)

        skill = MemorySkill()
        await skill.execute("show test-show", ctx)


class TestMemorySkillDelete:
    @patch("deep_coder.skills.memory.print_error")
    async def test_delete_empty_id(self, mock_error, ctx):
        skill = MemorySkill()
        await skill.execute("delete", ctx)
        mock_error.assert_called()

    @patch("deep_coder.skills.memory.print_error")
    async def test_delete_not_found(self, mock_error, ctx):
        skill = MemorySkill()
        await skill.execute("delete nonexistent", ctx)
        mock_error.assert_called()


class TestMemorySkillFallback:
    @patch("deep_coder.skills.memory.print_info")
    async def test_unknown_subcommand_treated_as_search(self, mock_info, ctx):
        skill = MemorySkill()
        await skill.execute("something random", ctx)
        mock_info.assert_called()
