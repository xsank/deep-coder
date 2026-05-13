"""Tests for the prompt system."""

from __future__ import annotations

import tempfile
from pathlib import Path

from deep_coder.prompts.system import (
    _find_coder_md,
    get_orchestrator_prompt,
    get_worker_prompt,
    load_prompt,
)


class TestLoadPrompt:
    def test_load_orchestrator(self):
        text = load_prompt("orchestrator")
        assert isinstance(text, str)
        assert len(text) > 0

    def test_load_worker(self):
        text = load_prompt("worker")
        assert isinstance(text, str)
        assert len(text) > 0


class TestFindCoderMd:
    def test_finds_coder_md(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "CODER.md").write_text("# Project\nSome rules.")
            result = _find_coder_md(d)
            assert result is not None
            assert "Project" in result

    def test_no_coder_md(self):
        with tempfile.TemporaryDirectory() as d:
            result = _find_coder_md(d)
            assert result is None

    def test_none_cwd(self):
        assert _find_coder_md(None) is None

    def test_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "CODER.md").write_text("x" * 20000)
            result = _find_coder_md(d)
            assert result is not None
            assert "truncated" in result
            assert len(result) < 20000


class TestGetOrchestratorPrompt:
    def test_basic(self):
        prompt = get_orchestrator_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_with_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            prompt = get_orchestrator_prompt(
                cwd=d,
                cached_coder_md=None,
                cached_memories=None,
            )
            assert d in prompt

    def test_with_coder_md(self):
        prompt = get_orchestrator_prompt(
            cached_coder_md="# My Project Rules",
            cached_memories=None,
        )
        assert "My Project Rules" in prompt

    def test_with_memories(self):
        prompt = get_orchestrator_prompt(
            cached_coder_md=None,
            cached_memories="**[feedback] Rule**: always lint",
        )
        assert "always lint" in prompt


class TestGetWorkerPrompt:
    def test_basic(self):
        prompt = get_worker_prompt(
            task_description="Read the file",
            cached_coder_md=None,
            cached_memories=None,
        )
        assert "Read the file" in prompt

    def test_with_context(self):
        prompt = get_worker_prompt(
            task_description="Fix the bug",
            task_context="Error in line 42",
            cached_coder_md=None,
            cached_memories=None,
        )
        assert "Fix the bug" in prompt
        assert "Error in line 42" in prompt

    def test_with_conversation_summary(self):
        prompt = get_worker_prompt(
            task_description="Continue work",
            conversation_summary="User asked about auth",
            cached_coder_md=None,
            cached_memories=None,
        )
        assert "User asked about auth" in prompt
