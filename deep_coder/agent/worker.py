"""Worker agent — executes a single task using Flash model with tool calls."""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine, Optional

from deep_coder.agent.task import Task
from deep_coder.client import DeepSeekClient
from deep_coder.display import print_file_diff
from deep_coder.models import ModelRole
from deep_coder.prompts.system import get_worker_prompt
from deep_coder.tools.base import ToolRegistry

OnWorkerStatus = Optional[Callable[[str, str, str], Coroutine[Any, Any, None]]]


def _make_assistant_msg(response: dict[str, Any]) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": response.get("content")}
    if response.get("reasoning_content"):
        msg["reasoning_content"] = response["reasoning_content"]
    if response.get("tool_calls"):
        msg["tool_calls"] = response["tool_calls"]
    return msg


class Worker:
    """Executes a single subtask using DeepSeek V4 Flash with tool access."""

    def __init__(self, client: DeepSeekClient, tool_registry: ToolRegistry) -> None:
        self.client = client
        self.tool_registry = tool_registry

    async def execute(
        self,
        task: Task,
        on_status: Any = None,
        on_worker_status: OnWorkerStatus = None,
    ) -> str:
        task.mark_running()
        if on_status:
            await on_status(task, "running")
        if on_worker_status:
            await on_worker_status(task.id, "running", "starting")

        system_prompt = get_worker_prompt(task.description, task.context)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.description},
        ]
        tools = self.tool_registry.to_openai_tools()

        max_iterations = 15
        for iteration in range(max_iterations):
            if on_worker_status:
                await on_worker_status(task.id, "running", f"thinking ({iteration + 1}/{max_iterations})")

            response = await self.client.chat_complete(
                messages=messages,
                model_role=ModelRole.FLASH,
                tools=tools if tools else None,
            )

            if response.get("tool_calls"):
                messages.append(_make_assistant_msg(response))
                for tc in response["tool_calls"]:
                    fn = tc["function"]
                    tool_name = fn["name"]

                    if on_worker_status:
                        await on_worker_status(task.id, "running", f"tool: {tool_name}")
                    if on_status:
                        await on_status(task, f"tool:{tool_name}")

                    result = await self.tool_registry.dispatch(tool_name, fn["arguments"])
                    if result.success and result.metadata and "old_content" in result.metadata:
                        print_file_diff(
                            result.metadata["file_path"],
                            result.metadata["old_content"],
                            result.metadata["new_content"],
                        )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result.content,
                    })
            else:
                content = response.get("content") or ""
                task.mark_completed(content)
                if on_status:
                    await on_status(task, "completed")
                if on_worker_status:
                    await on_worker_status(task.id, "completed", "done")
                return content

        task.mark_failed("Max iterations reached without completing the task")
        if on_status:
            await on_status(task, "failed")
        if on_worker_status:
            await on_worker_status(task.id, "failed", "max iterations")
        return "Error: max iterations reached"
