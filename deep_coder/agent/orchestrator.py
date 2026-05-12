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
from deep_coder.display import (
    TaskProgressDisplay,
    console,
    print_phase,
    print_plan_summary,
)
from deep_coder.models import ModelRole
from deep_coder.prompts.system import get_orchestrator_prompt
from deep_coder.tools.base import ToolRegistry


def _make_assistant_msg(response: dict[str, Any]) -> dict[str, Any]:
    """Build an assistant message dict, preserving reasoning_content if present."""
    msg: dict[str, Any] = {"role": "assistant", "content": response.get("content")}
    if response.get("reasoning_content"):
        msg["reasoning_content"] = response["reasoning_content"]
    if response.get("tool_calls"):
        msg["tool_calls"] = response["tool_calls"]
    return msg


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

        print_phase("planning", "analyzing request...")

        response = await self.client.collect_stream(
            messages=messages,
            model_role=ModelRole.PRO,
            on_token=None,
        )

        content = response.get("content") or ""

        plan = self._try_extract_plan(content)
        if plan and len(plan.tasks) > 0:
            plan_tasks_info = [
                {"id": t.id, "desc": t.description[:60], "deps": t.depends_on}
                for t in plan.tasks
            ]
            print_plan_summary(plan.description, plan_tasks_info)

            n = len(plan.tasks)
            print_phase("executing", f"{n} task{'s' if n > 1 else ''}")
            await self._execute_plan_with_progress(plan)

            print_phase("verifying", "reviewing results...")
            verification = await self._verify_results(plan, user_message)
            self.conversation.append({"role": "assistant", "content": verification})
            from deep_coder.display import Markdown as RichMarkdown
            console.print()
            console.print(RichMarkdown(verification))
            console.print()
            return ""

        if on_token and content:
            for char in content:
                await on_token(char)

        self.conversation.append(_make_assistant_msg(response))
        return content

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

    async def _execute_plan_with_progress(self, plan: Plan) -> None:
        """Execute plan with live progress display showing all task states."""
        progress = TaskProgressDisplay()
        await progress.start(plan.tasks)

        max_concurrent = self.config.agent.max_workers

        async def on_worker_status(task_id: str, status: str, detail: str) -> None:
            await progress.update(task_id, status, detail)

        try:
            while not plan.is_complete:
                ready = plan.get_ready_tasks()
                if not ready:
                    break

                batch = ready[:max_concurrent]
                coros = [
                    self._run_worker(task, on_worker_status=on_worker_status)
                    for task in batch
                ]
                await asyncio.gather(*coros)
        finally:
            await progress.stop()

        completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)
        summary_parts = [f"[green]{completed} completed[/green]"]
        if failed:
            summary_parts.append(f"[red]{failed} failed[/red]")
        console.print(f"  [dim]Results:[/dim] {', '.join(summary_parts)}\n")

    async def _run_worker(
        self,
        task: Task,
        on_status: Any = None,
        on_worker_status: Any = None,
    ) -> None:
        try:
            await self.worker.execute(task, on_status=on_status, on_worker_status=on_worker_status)
        except Exception as e:
            task.mark_failed(str(e))
            if on_worker_status:
                await on_worker_status(task.id, "failed", str(e)[:60])

    async def _verify_results(
        self,
        plan: Plan,
        original_request: str,
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
            f"Original user request: {original_request}\n\n"
            f"Plan: {plan.description}\n\n"
            f"Worker Results:\n\n"
            + "\n".join(results_summary)
            + "\n\nSummarize what was done in 2-5 concise bullet points. "
            "If there are issues, flag them. Do NOT repeat raw tool outputs or file contents. "
            "Do NOT use headers (no # or ##). Keep it short and actionable."
        )

        system_prompt = get_orchestrator_prompt(self._cwd)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": verification_prompt},
        ]

        response = await self.client.collect_stream(
            messages=messages,
            model_role=ModelRole.PRO,
        )
        return response.get("content") or ""

    async def compact(self, on_token: Any = None) -> str:
        """Compress conversation history using Flash model to free context space."""
        if len(self.conversation) < 2:
            return "Nothing to compact."

        history_text = ""
        for msg in self.conversation:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if content:
                history_text += f"[{role}]: {content[:500]}\n"

        compact_prompt = (
            "Summarize the following conversation history concisely. "
            "Preserve: key decisions, file paths mentioned, code changes made, "
            "open questions, and current task state. "
            "Drop: greetings, verbose tool outputs, redundant details.\n\n"
            f"{history_text}"
        )

        response = await self.client.collect_stream(
            messages=[
                {"role": "system", "content": "You are a conversation summarizer. Be concise."},
                {"role": "user", "content": compact_prompt},
            ],
            model_role=ModelRole.FLASH,
            on_token=on_token,
        )

        summary = response.get("content") or ""
        old_count = len(self.conversation)
        self.conversation = [
            {"role": "system", "content": f"[Compacted history — {old_count} messages]\n{summary}"},
        ]
        return summary

    def export_conversation(self) -> list[dict[str, Any]]:
        return list(self.conversation)

    def import_conversation(self, messages: list[dict[str, Any]]) -> None:
        self.conversation = list(messages)

    def clear_history(self) -> None:
        self.conversation.clear()
