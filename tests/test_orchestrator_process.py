"""Tests for orchestrator process() — greeting path, plan extraction, compact."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deep_coder.agent.orchestrator import Orchestrator
from deep_coder.client import DeepSeekClient
from deep_coder.config import AgentConfig, Config, ModelConfig
from deep_coder.tools.base import ToolRegistry


@pytest.fixture
def setup():
    config = Config(
        model=ModelConfig(api_key="test", context_limit=100000),
        agent=AgentConfig(max_workers=2),
    )
    client = DeepSeekClient(config)
    registry = ToolRegistry()
    orch = Orchestrator(client, config, registry)
    orch.set_cwd("/tmp/test")
    return orch, client


class TestProcessGreeting:
    async def test_greeting_uses_flash(self, setup):
        orch, client = setup
        tokens = []

        async def on_token(t):
            tokens.append(t)

        client.collect_stream = AsyncMock(return_value={"content": "Hi there!", "tool_calls": None})

        result = await orch.process("hi", on_token=on_token)
        assert result == "Hi there!"
        assert len(orch.conversation) == 2
        assert orch.conversation[0]["role"] == "user"
        assert orch.conversation[1]["role"] == "assistant"


class TestProcessTextResponse:
    @patch("deep_coder.context.collect_project_context", new_callable=AsyncMock, return_value=None)
    @patch("deep_coder.agent.orchestrator.get_orchestrator_prompt", return_value="sys prompt")
    @patch("deep_coder.agent.orchestrator.ReasoningStreamDisplay")
    async def test_text_response_no_plan(self, mock_display_cls, mock_prompt, mock_ctx, setup):
        orch, client = setup

        mock_display = MagicMock()
        mock_display.start = AsyncMock()
        mock_display.stop = AsyncMock()
        mock_display.on_reasoning = AsyncMock()
        mock_display_cls.return_value = mock_display

        client.collect_stream = AsyncMock(
            return_value={
                "content": "Python is a great language for beginners.",
                "tool_calls": None,
            }
        )
        orch._prompt_cache_loaded = True
        orch._cached_coder_md = None
        orch._cached_memories = None

        tokens = []

        async def on_token(t):
            tokens.append(t)

        result = await orch.process("What is Python?", on_token=on_token)
        assert "Python" in result
        assert len(orch.conversation) == 2


class TestProcessPlan:
    @patch("deep_coder.context.collect_project_context", new_callable=AsyncMock, return_value=None)
    @patch("deep_coder.agent.orchestrator.get_orchestrator_prompt", return_value="sys prompt")
    @patch("deep_coder.agent.orchestrator.ReasoningStreamDisplay")
    @patch("deep_coder.agent.orchestrator.print_plan_summary")
    async def test_plan_extraction_and_execution(
        self, mock_plan_summary, mock_display_cls, mock_prompt, mock_ctx, setup
    ):
        orch, client = setup
        orch._prompt_cache_loaded = True
        orch._cached_coder_md = None
        orch._cached_memories = None

        mock_display = MagicMock()
        mock_display.start = AsyncMock()
        mock_display.stop = AsyncMock()
        mock_display.on_reasoning = AsyncMock()
        mock_display_cls.return_value = mock_display

        plan_json = (
            '```json\n{"plan": "Test plan",'
            ' "tasks": [{"id": "t1", "description": "Do task 1"}]}\n```'
        )

        client.collect_stream = AsyncMock(
            return_value={
                "content": plan_json,
                "tool_calls": None,
            }
        )

        with patch.object(
            orch, "_run_plan_loop", new_callable=AsyncMock, return_value="Plan completed"
        ):
            result = await orch.process("Add a login feature")
            assert result == ""

    @patch("deep_coder.context.collect_project_context", new_callable=AsyncMock, return_value=None)
    @patch("deep_coder.agent.orchestrator.get_orchestrator_prompt", return_value="sys prompt")
    @patch("deep_coder.agent.orchestrator.ReasoningStreamDisplay")
    async def test_plan_rejected(self, mock_display_cls, mock_prompt, mock_ctx, setup):
        orch, client = setup
        orch._prompt_cache_loaded = True
        orch._cached_coder_md = None
        orch._cached_memories = None

        mock_display = MagicMock()
        mock_display.start = AsyncMock()
        mock_display.stop = AsyncMock()
        mock_display.on_reasoning = AsyncMock()
        mock_display_cls.return_value = mock_display

        plan_json = (
            '```json\n{"plan": "Test", "tasks": [{"id": "t1", "description": "Do it"}]}\n```'
        )

        client.collect_stream = AsyncMock(return_value={"content": plan_json, "tool_calls": None})

        async def reject_plan(desc, tasks):
            return "no"

        orch._on_plan_approval = reject_plan

        with patch("deep_coder.agent.orchestrator.print_plan_summary"):
            result = await orch.process("Do something")
            assert result == ""
            assert "(Plan rejected" in orch.conversation[-1]["content"]


class TestCompact:
    async def test_compact_empty(self, setup):
        orch, _ = setup
        result = await orch.compact()
        assert result == "Nothing to compact."

    async def test_compact_conversation(self, setup):
        orch, client = setup
        orch.conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm good!"},
        ]

        client.collect_stream = AsyncMock(
            return_value={"content": "Compacted summary: user greeted, assistant responded."}
        )

        result = await orch.compact()
        assert "Compacted" in result or "summary" in result.lower()
        assert len(orch.conversation) == 1
        assert "Compacted" in orch.conversation[0]["content"]


class TestEnsurePromptCache:
    @patch("deep_coder.prompts.system._find_coder_md", return_value="# CODER.md content")
    @patch("deep_coder.prompts.system._load_memories", return_value="memories")
    def test_loads_once(self, mock_mem, mock_coder, setup):
        orch, _ = setup
        orch._ensure_prompt_cache()
        assert orch._prompt_cache_loaded
        assert orch._cached_coder_md == "# CODER.md content"
        assert orch._cached_memories == "memories"

        orch._ensure_prompt_cache()
        assert mock_coder.call_count == 1

    @patch("deep_coder.prompts.system._find_coder_md", return_value=None)
    @patch("deep_coder.prompts.system._load_memories", return_value=None)
    def test_invalidate_reloads(self, mock_mem, mock_coder, setup):
        orch, _ = setup
        orch._ensure_prompt_cache()
        orch.invalidate_prompt_cache()
        orch._ensure_prompt_cache()
        assert mock_coder.call_count == 2
