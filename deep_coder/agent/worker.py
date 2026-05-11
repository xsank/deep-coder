"""Worker agent — executes a single task using Flash model with tool calls."""

from __future__ import annotations

import json
from typing import Any

from deep_coder.agent.task import Task
from deep_coder.client import DeepSeekClient
from deep_coder.models import ModelRole
from deep_coder.prompts.system import get_worker_prompt
from deep_coder.tools.base import ToolRegistry


class Worker:
    """Executes a single subtask using DeepSeek V4 Flash with tool access."""

    def __init__(self, client: DeepSeekClient, tool_registry: ToolRegistry) -> None:
        self.client = client
        self.tool_registry = tool_registry

    async def execute(self, task: Task, on_status: Any = None) -> str:
        task.mark_running()
        if on_status:
            await on_status(task, "running")

        system_prompt = get_worker_prompt(task.description, task.context)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.description},
        ]
        tools = self.tool_registry.to_openai_tools()

        max_iterations = 15
        for _ in range(max_iterations):
            response = await self.client.chat_complete(
                messages=messages,
                model_role=ModelRole.FLASH,
                tools=tools if tools else None,
            )

            if response.get("tool_calls"):
                messages.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": response["tool_calls"],
                })
                for tc in response["tool_calls"]:
                    fn = tc["function"]
                    result = await self.tool_registry.dispatch(fn["name"], fn["arguments"])
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result.content,
                    })
                    if on_status:
                        status_msg = f"tool:{fn['name']}"
                        await on_status(task, status_msg)
            else:
                content = response.get("content") or ""
                task.mark_completed(content)
                if on_status:
                    await on_status(task, "completed")
                return content

        task.mark_failed("Max iterations reached without completing the task")
        if on_status:
            await on_status(task, "failed")
        return "Error: max iterations reached"
