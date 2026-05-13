"""Async DeepSeek API client (OpenAI-compatible)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from deep_coder.config import Config
from deep_coder.models import ModelRole

_DSML_TAG_RE = re.compile(r"</?[｜|]*DSML[｜|]*[^>]*>")


def strip_dsml(content: str) -> str:
    """Remove DeepSeek internal markup (DSML tags) leaked into text content."""
    if "DSML" not in content:
        return content
    first = last = None
    for m in _DSML_TAG_RE.finditer(content):
        if first is None:
            first = m.start()
        last = m.end()
    if first is not None and last is not None:
        content = content[:first] + content[last:]
    return content.strip()


COST_PER_MILLION = {
    "deepseek-v4-pro": {"input": 2.0, "output": 8.0},
    "deepseek-v4-flash": {"input": 0.5, "output": 2.0},
}
DEFAULT_COST = {"input": 1.0, "output": 4.0}


@dataclass
class UsageStats:
    """Tracks cumulative token usage and cost across API calls."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_requests: int = 0
    pro_prompt_tokens: int = 0
    pro_completion_tokens: int = 0
    pro_requests: int = 0
    flash_prompt_tokens: int = 0
    flash_completion_tokens: int = 0
    flash_requests: int = 0
    start_time: float = field(default_factory=time.time)

    def record(self, model_role: ModelRole, prompt_tokens: int, completion_tokens: int) -> None:
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_requests += 1
        if model_role == ModelRole.PRO:
            self.pro_prompt_tokens += prompt_tokens
            self.pro_completion_tokens += completion_tokens
            self.pro_requests += 1
        else:
            self.flash_prompt_tokens += prompt_tokens
            self.flash_completion_tokens += completion_tokens
            self.flash_requests += 1

    def estimated_cost(self, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = COST_PER_MILLION.get(model_id, DEFAULT_COST)
        return (prompt_tokens * rates["input"] + completion_tokens * rates["output"]) / 1_000_000

    @property
    def total_cost(self) -> float:
        pro_cost = self.estimated_cost(
            "deepseek-v4-pro",
            self.pro_prompt_tokens,
            self.pro_completion_tokens,
        )
        flash_cost = self.estimated_cost(
            "deepseek-v4-flash",
            self.flash_prompt_tokens,
            self.flash_completion_tokens,
        )
        return pro_cost + flash_cost

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def reset(self) -> None:
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0
        self.pro_prompt_tokens = 0
        self.pro_completion_tokens = 0
        self.pro_requests = 0
        self.flash_prompt_tokens = 0
        self.flash_completion_tokens = 0
        self.flash_requests = 0
        self.start_time = time.time()


class DeepSeekClient:
    """Async client for the DeepSeek API using OpenAI-compatible SDK."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.usage = UsageStats()
        self._client = AsyncOpenAI(
            api_key=config.model.api_key or "sk-placeholder",
            base_url=config.model.base_url,
        )

    def _get_model_id(self, role: ModelRole) -> str:
        if role == ModelRole.PRO:
            return self.config.model.pro_model
        return self.config.model.flash_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model_role: ModelRole = ModelRole.FLASH,
        tools: Optional[list[dict[str, Any]]] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        model = self._get_model_id(model_role)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": (
                temperature if temperature is not None else self.config.model.temperature
            ),
            "max_tokens": max_tokens or self.config.model.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return await self._client.chat.completions.create(**kwargs)

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model_role: ModelRole = ModelRole.FLASH,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[ChatCompletionChunk]:
        response = await self.chat(
            messages=messages,
            model_role=model_role,
            tools=tools,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        async for chunk in response:
            yield chunk

    async def chat_complete(
        self,
        messages: list[dict[str, Any]],
        model_role: ModelRole = ModelRole.FLASH,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        response = await self.chat(
            messages=messages,
            model_role=model_role,
            tools=tools,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        self.usage.record(model_role, prompt_tokens, completion_tokens)
        result: dict[str, Any] = {
            "role": "assistant",
            "content": choice.message.content,
            "tool_calls": None,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": (prompt_tokens + completion_tokens),
            },
        }
        reasoning_content = getattr(choice.message, "reasoning_content", None)
        if reasoning_content:
            result["reasoning_content"] = reasoning_content
        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
        return result

    async def collect_stream(
        self,
        messages: list[dict[str, Any]],
        model_role: ModelRole = ModelRole.FLASH,
        tools: Optional[list[dict[str, Any]]] = None,
        on_token: Optional[Any] = None,
        on_reasoning: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Stream a response and collect the full result, calling on_token for each text delta."""
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls_map: dict[int, dict[str, Any]] = {}
        stream_usage_prompt = 0
        stream_usage_completion = 0

        async for chunk in self.chat_stream(messages, model_role, tools):
            if hasattr(chunk, "usage") and chunk.usage:
                stream_usage_prompt = getattr(chunk.usage, "prompt_tokens", 0) or 0
                stream_usage_completion = getattr(chunk.usage, "completion_tokens", 0) or 0
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            reasoning_content = getattr(delta, "reasoning_content", None)
            if reasoning_content:
                reasoning_parts.append(reasoning_content)
                if on_reasoning:
                    await on_reasoning(reasoning_content)

            if delta.content:
                content_parts.append(delta.content)
                if on_token:
                    await on_token(delta.content)

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": tc_delta.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    entry = tool_calls_map[idx]
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["function"]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["function"]["arguments"] += tc_delta.function.arguments

        if stream_usage_prompt or stream_usage_completion:
            self.usage.record(model_role, stream_usage_prompt, stream_usage_completion)
        else:
            est_prompt = sum(len(m.get("content", "") or "") // 4 for m in messages)
            est_completion = sum(len(p) for p in content_parts) // 4
            self.usage.record(model_role, est_prompt, est_completion)

        raw_content = "".join(content_parts) if content_parts else None
        result: dict[str, Any] = {
            "role": "assistant",
            "content": strip_dsml(raw_content) if raw_content else None,
            "tool_calls": None,
        }
        if reasoning_parts:
            result["reasoning_content"] = "".join(reasoning_parts)
        if tool_calls_map:
            result["tool_calls"] = [tool_calls_map[i] for i in sorted(tool_calls_map)]
        return result
