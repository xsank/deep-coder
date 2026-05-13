"""Extended tests for client.py — strip_dsml, UsageStats, DeepSeekClient methods."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from deep_coder.client import (
    DEFAULT_COST,
    DeepSeekClient,
    UsageStats,
    strip_dsml,
)
from deep_coder.config import Config, ModelConfig
from deep_coder.models import ModelRole


class TestStripDsml:
    def test_no_dsml_returns_unchanged(self):
        assert strip_dsml("hello world") == "hello world"

    def test_empty_string(self):
        assert strip_dsml("") == ""

    def test_single_dsml_tag(self):
        result = strip_dsml("before<DSML>content</DSML>after")
        assert result == "beforeafter"

    def test_dsml_with_pipe(self):
        result = strip_dsml("before<|DSML|>inner</|DSML|>after")
        assert result == "beforeafter"

    def test_dsml_with_fullwidth_pipe(self):
        result = strip_dsml("start<｜DSML｜>stuff</｜DSML｜>end")
        assert result == "startend"

    def test_dsml_with_attributes(self):
        result = strip_dsml("text<DSML type='code'>hidden</DSML>more")
        assert result == "textmore"

    def test_dsml_only(self):
        result = strip_dsml("<DSML>only dsml content</DSML>")
        assert result == ""

    def test_dsml_with_whitespace(self):
        result = strip_dsml("  <DSML>x</DSML>  text  ")
        assert result == "text"

    def test_no_dsml_keyword_short_circuits(self):
        text = "just regular text without the keyword"
        assert strip_dsml(text) == text


class TestUsageStats:
    def test_initial_values(self):
        stats = UsageStats()
        assert stats.total_prompt_tokens == 0
        assert stats.total_completion_tokens == 0
        assert stats.total_requests == 0
        assert stats.pro_requests == 0
        assert stats.flash_requests == 0

    def test_record_pro(self):
        stats = UsageStats()
        stats.record(ModelRole.PRO, 100, 50)
        assert stats.total_prompt_tokens == 100
        assert stats.total_completion_tokens == 50
        assert stats.total_requests == 1
        assert stats.pro_prompt_tokens == 100
        assert stats.pro_completion_tokens == 50
        assert stats.pro_requests == 1
        assert stats.flash_requests == 0

    def test_record_flash(self):
        stats = UsageStats()
        stats.record(ModelRole.FLASH, 200, 100)
        assert stats.flash_prompt_tokens == 200
        assert stats.flash_completion_tokens == 100
        assert stats.flash_requests == 1
        assert stats.pro_requests == 0

    def test_record_multiple(self):
        stats = UsageStats()
        stats.record(ModelRole.PRO, 100, 50)
        stats.record(ModelRole.FLASH, 200, 100)
        stats.record(ModelRole.FLASH, 300, 150)
        assert stats.total_requests == 3
        assert stats.pro_requests == 1
        assert stats.flash_requests == 2
        assert stats.total_prompt_tokens == 600
        assert stats.total_completion_tokens == 300

    def test_estimated_cost_known_model(self):
        stats = UsageStats()
        cost = stats.estimated_cost("deepseek-v4-pro", 1_000_000, 1_000_000)
        expected = 2.0 + 8.0
        assert cost == expected

    def test_estimated_cost_flash(self):
        stats = UsageStats()
        cost = stats.estimated_cost("deepseek-v4-flash", 1_000_000, 1_000_000)
        expected = 0.5 + 2.0
        assert cost == expected

    def test_estimated_cost_unknown_model(self):
        stats = UsageStats()
        cost = stats.estimated_cost("unknown-model", 1_000_000, 1_000_000)
        expected = DEFAULT_COST["input"] + DEFAULT_COST["output"]
        assert cost == expected

    def test_total_cost(self):
        stats = UsageStats()
        stats.record(ModelRole.PRO, 1_000_000, 500_000)
        stats.record(ModelRole.FLASH, 2_000_000, 1_000_000)
        pro_cost = stats.estimated_cost("deepseek-v4-pro", 1_000_000, 500_000)
        flash_cost = stats.estimated_cost("deepseek-v4-flash", 2_000_000, 1_000_000)
        assert stats.total_cost == pro_cost + flash_cost

    def test_total_cost_zero_initially(self):
        stats = UsageStats()
        assert stats.total_cost == 0.0

    def test_elapsed_seconds(self):
        stats = UsageStats()
        stats.start_time = time.time() - 10
        elapsed = stats.elapsed_seconds
        assert 9.5 <= elapsed <= 11.0

    def test_reset(self):
        stats = UsageStats()
        stats.record(ModelRole.PRO, 100, 50)
        stats.record(ModelRole.FLASH, 200, 100)
        stats.reset()
        assert stats.total_prompt_tokens == 0
        assert stats.total_completion_tokens == 0
        assert stats.total_requests == 0
        assert stats.pro_requests == 0
        assert stats.flash_requests == 0
        assert stats.flash_prompt_tokens == 0
        assert stats.flash_completion_tokens == 0


class TestDeepSeekClientInit:
    def test_placeholder_key(self):
        config = Config(model=ModelConfig(api_key=""))
        client = DeepSeekClient(config)
        assert client._client.api_key == "sk-placeholder"

    def test_custom_key(self):
        config = Config(model=ModelConfig(api_key="sk-real"))
        client = DeepSeekClient(config)
        assert client._client.api_key == "sk-real"

    def test_get_model_id_pro(self):
        config = Config(model=ModelConfig(pro_model="my-pro"))
        client = DeepSeekClient(config)
        assert client._get_model_id(ModelRole.PRO) == "my-pro"

    def test_get_model_id_flash(self):
        config = Config(model=ModelConfig(flash_model="my-flash"))
        client = DeepSeekClient(config)
        assert client._get_model_id(ModelRole.FLASH) == "my-flash"


class TestDeepSeekClientChat:
    @pytest.fixture
    def client(self):
        config = Config()
        return DeepSeekClient(config)

    async def test_chat_builds_kwargs(self, client):
        mock_create = AsyncMock()
        client._client.chat.completions.create = mock_create

        await client.chat(
            messages=[{"role": "user", "content": "hi"}],
            model_role=ModelRole.FLASH,
            tools=[{"type": "function", "function": {"name": "test"}}],
            temperature=0.5,
            max_tokens=100,
        )

        mock_create.assert_called_once()
        kwargs = mock_create.call_args[1]
        assert kwargs["model"] == client.config.model.flash_model
        assert kwargs["tools"] == [{"type": "function", "function": {"name": "test"}}]
        assert kwargs["tool_choice"] == "auto"
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 100

    async def test_chat_no_tools(self, client):
        mock_create = AsyncMock()
        client._client.chat.completions.create = mock_create

        await client.chat(
            messages=[{"role": "user", "content": "hi"}],
        )

        kwargs = mock_create.call_args[1]
        assert "tools" not in kwargs
        assert "tool_choice" not in kwargs

    async def test_chat_complete(self, client):
        mock_msg = MagicMock()
        mock_msg.content = "Hello!"
        mock_msg.reasoning_content = None
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat_complete(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result["role"] == "assistant"
        assert result["content"] == "Hello!"
        assert result["tool_calls"] is None
        assert result["usage"]["prompt_tokens"] == 10
        assert result["usage"]["completion_tokens"] == 5
        assert client.usage.total_requests == 1

    async def test_chat_complete_with_tool_calls(self, client):
        mock_tc = MagicMock()
        mock_tc.id = "tc_1"
        mock_tc.function.name = "read_file"
        mock_tc.function.arguments = '{"path": "a.py"}'

        mock_msg = MagicMock()
        mock_msg.content = None
        mock_msg.reasoning_content = None
        mock_msg.tool_calls = [mock_tc]

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=3)

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat_complete(
            messages=[{"role": "user", "content": "read a.py"}],
        )

        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["function"]["name"] == "read_file"

    async def test_chat_complete_with_reasoning(self, client):
        mock_msg = MagicMock()
        mock_msg.content = "Answer"
        mock_msg.reasoning_content = "Let me think..."
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat_complete(
            messages=[{"role": "user", "content": "think"}],
        )

        assert result["reasoning_content"] == "Let me think..."

    async def test_chat_complete_no_usage(self, client):
        mock_msg = MagicMock()
        mock_msg.content = "ok"
        mock_msg.reasoning_content = None
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.chat_complete(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result["usage"]["prompt_tokens"] == 0
        assert result["usage"]["completion_tokens"] == 0


class TestCollectStream:
    @pytest.fixture
    def client(self):
        config = Config()
        return DeepSeekClient(config)

    def _make_chunk(
        self,
        content: str | None = None,
        reasoning: str | None = None,
        tool_calls: list | None = None,
        usage=None,
    ):
        chunk = MagicMock()
        chunk.usage = usage

        delta = MagicMock()
        delta.content = content
        delta.reasoning_content = reasoning
        delta.tool_calls = tool_calls

        choice = MagicMock()
        choice.delta = delta
        chunk.choices = [choice]
        return chunk

    async def test_collect_text_stream(self, client):
        chunks = [
            self._make_chunk(content="Hello"),
            self._make_chunk(content=" world"),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        tokens = []

        async def on_token(t):
            tokens.append(t)

        result = await client.collect_stream(
            messages=[{"role": "user", "content": "hi"}],
            on_token=on_token,
        )

        assert result["content"] == "Hello world"
        assert tokens == ["Hello", " world"]

    async def test_collect_reasoning_stream(self, client):
        chunks = [
            self._make_chunk(reasoning="thinking..."),
            self._make_chunk(content="Answer"),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        reasoning = []

        async def on_reasoning(t):
            reasoning.append(t)

        result = await client.collect_stream(
            messages=[{"role": "user", "content": "think"}],
            on_reasoning=on_reasoning,
        )

        assert result["reasoning_content"] == "thinking..."
        assert result["content"] == "Answer"
        assert reasoning == ["thinking..."]

    async def test_collect_tool_calls(self, client):
        tc_delta1 = MagicMock()
        tc_delta1.index = 0
        tc_delta1.id = "tc_1"
        tc_delta1.function = MagicMock()
        tc_delta1.function.name = "read_file"
        tc_delta1.function.arguments = '{"path":'

        tc_delta2 = MagicMock()
        tc_delta2.index = 0
        tc_delta2.id = None
        tc_delta2.function = MagicMock()
        tc_delta2.function.name = None
        tc_delta2.function.arguments = ' "a.py"}'

        chunks = [
            self._make_chunk(tool_calls=[tc_delta1]),
            self._make_chunk(tool_calls=[tc_delta2]),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        result = await client.collect_stream(
            messages=[{"role": "user", "content": "read"}],
        )

        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1
        tc = result["tool_calls"][0]
        assert tc["function"]["name"] == "read_file"
        assert tc["function"]["arguments"] == '{"path": "a.py"}'

    async def test_collect_stream_with_usage(self, client):
        usage_obj = MagicMock()
        usage_obj.prompt_tokens = 42
        usage_obj.completion_tokens = 15

        chunks = [
            self._make_chunk(content="hi", usage=usage_obj),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        await client.collect_stream(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert client.usage.total_prompt_tokens == 42
        assert client.usage.total_completion_tokens == 15

    async def test_collect_stream_estimates_without_usage(self, client):
        chunks = [
            self._make_chunk(content="response text"),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        await client.collect_stream(
            messages=[{"role": "user", "content": "hello world"}],
        )

        assert client.usage.total_requests == 1
        assert client.usage.total_prompt_tokens > 0

    async def test_collect_stream_empty_choices(self, client):
        empty_chunk = MagicMock()
        empty_chunk.usage = None
        empty_chunk.choices = []

        text_chunk = self._make_chunk(content="ok")

        async def mock_stream(*args, **kwargs):
            yield empty_chunk
            yield text_chunk

        client.chat_stream = mock_stream

        result = await client.collect_stream(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result["content"] == "ok"

    async def test_collect_stream_dsml_stripped(self, client):
        chunks = [
            self._make_chunk(content="before<DSML>hidden</DSML>after"),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        result = await client.collect_stream(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert "DSML" not in result["content"]
        assert "beforeafter" in result["content"]

    async def test_collect_stream_no_content(self, client):
        chunks = [
            self._make_chunk(content=None),
        ]

        async def mock_stream(*args, **kwargs):
            for c in chunks:
                yield c

        client.chat_stream = mock_stream

        result = await client.collect_stream(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result["content"] is None
