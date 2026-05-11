"""Async DeepSeek API client (OpenAI-compatible)."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from deep_coder.config import Config
from deep_coder.models import ModelRole


class DeepSeekClient:
    """Async client for the DeepSeek API using OpenAI-compatible SDK."""

    def __init__(self, config: Config) -> None:
        self.config = config
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
            "temperature": temperature if temperature is not None else self.config.model.temperature,
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
        result: dict[str, Any] = {
            "role": "assistant",
            "content": choice.message.content,
            "tool_calls": None,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }
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
    ) -> dict[str, Any]:
        """Stream a response and collect the full result, calling on_token for each text delta."""
        content_parts: list[str] = []
        tool_calls_map: dict[int, dict[str, Any]] = {}

        async for chunk in self.chat_stream(messages, model_role, tools):
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

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

        result: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(content_parts) if content_parts else None,
            "tool_calls": None,
        }
        if tool_calls_map:
            result["tool_calls"] = [tool_calls_map[i] for i in sorted(tool_calls_map)]
        return result
