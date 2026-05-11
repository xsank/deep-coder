"""Orchestrator agent — uses Pro model for planning and verification, Flash for execution."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional

from deep_coder.agent.task import Plan, Task, TaskStatus
from deep_coder.agent.worker import Worker
from deep_coder.client import DeepSeekClient
from deep_coder.config import Config
from deep_coder.models import ModelRole
from deep_coder.prompts.system import get_orchestrator_prompt
from deep_coder.tools.base import ToolRegistry


class Orchestrator:
    """Two-tier agent: Pro for planning/verification, Flash workers for execution."""

    def __init__(self, client: DeepSeekClient, config: Config, tool_registry: ToolRegistry) -> None:
        self.client = client
        self.config = config
        self.tool_registry = tool_registry
        self.worker = Worker(client, tool_registry)
        self.conversation: list[dict[str, Any]] = []
        self._cwd: Optional[str] = None

    def set_cwd(self, cwd: str) -> None:
        self._cwd = cwd

    async def process(
        self,
        user_message: str,
        on_token: Any = None,
        on_status: Any = None,
    ) -> str:
        self.conversation.append({"role": "user", "content": user_message})

        system_prompt = get_orchestrator_prompt(self._cwd)
        messages = [{"role": "system", "content": system_prompt}] + self.conversation
        tools = self.tool_registry.to_openai_tools()

        response = await self.client.collect_stream(
            messages=messages,
            model_role=ModelRole.PRO,
            tools=tools,
            on_token=on_token,
        )

        if response.get("tool_calls"):
            result = await self._handle_tool_calls(response, messages, tools, on_token, on_status)
            self.conversation.append({"role": "assistant", "content": result})
            return result

        content = response.get("content") or ""

        plan = self._try_extract_plan(content)
        if plan and len(plan.tasks) > 0:
            if on_status:
                await on_status(None, f"plan:{len(plan.tasks)} tasks")

            await self._execute_plan(plan, on_status)
            verification = await self._verify_results(plan, user_message, on_token)
            self.conversation.append({"role": "assistant", "content": verification})
            return verification

        self.conversation.append({"role": "assistant", "content": content})
        return content

    async def _handle_tool_calls(
        self,
        response: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_token: Any = None,
        on_status: Any = None,
    ) -> str:
        messages_copy = list(messages)
        current_response = response
        max_rounds = 10

        for _ in range(max_rounds):
            if not current_response.get("tool_calls"):
                return current_response.get("content") or ""

            messages_copy.append({
                "role": "assistant",
                "content": current_response.get("content"),
                "tool_calls": current_response["tool_calls"],
            })

            for tc in current_response["tool_calls"]:
                fn = tc["function"]
                if on_status:
                    await on_status(None, f"tool:{fn['name']}")
                result = await self.tool_registry.dispatch(fn["name"], fn["arguments"])
                messages_copy.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result.content,
                })

            current_response = await self.client.collect_stream(
                messages=messages_copy,
                model_role=ModelRole.PRO,
                tools=tools,
                on_token=on_token,
            )

        return current_response.get("content") or ""

    def _try_extract_plan(self, content: str) -> Optional[Plan]:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{[^{}]*\"tasks\"\s*:\s*\[.*?\]\s*\})", content, re.DOTALL)
        if not json_match:
            return None
        try:
            data = json.loads(json_match.group(1))
            if "tasks" in data and isinstance(data["tasks"], list):
                return Plan.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    async def _execute_plan(self, plan: Plan, on_status: Any = None) -> None:
        max_concurrent = self.config.agent.max_workers

        while not plan.is_complete:
            ready = plan.get_ready_tasks()
            if not ready:
                break

            batch = ready[:max_concurrent]
            tasks = [self._run_worker(task, on_status) for task in batch]
            await asyncio.gather(*tasks)

    async def _run_worker(self, task: Task, on_status: Any = None) -> None:
        try:
            await self.worker.execute(task, on_status)
        except Exception as e:
            task.mark_failed(str(e))
            if on_status:
                await on_status(task, f"failed:{e}")

    async def _verify_results(
        self,
        plan: Plan,
        original_request: str,
        on_token: Any = None,
    ) -> str:
        results_summary = []
        for task in plan.tasks:
            status = "COMPLETED" if task.status == TaskStatus.COMPLETED else "FAILED"
            result_text = task.result or task.error or "No output"
            results_summary.append(
                f"### Task: {task.id} [{status}]\n"
                f"Description: {task.description}\n"
                f"Result: {result_text}\n"
            )

        verification_prompt = (
            f"## Verification Request\n\n"
            f"Original user request: {original_request}\n\n"
            f"Plan: {plan.description}\n\n"
            f"## Worker Results\n\n"
            + "\n".join(results_summary)
            + "\n\nReview the results above. Provide a concise summary of what was accomplished. "
            "If there are any issues or incomplete tasks, flag them clearly."
        )

        system_prompt = get_orchestrator_prompt(self._cwd)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": verification_prompt},
        ]

        response = await self.client.collect_stream(
            messages=messages,
            model_role=ModelRole.PRO,
            on_token=on_token,
        )
        return response.get("content") or ""

    def clear_history(self) -> None:
        self.conversation.clear()
