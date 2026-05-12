"""Orchestrator agent — uses Pro model for planning and verification, Flash for execution."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Callable, Coroutine, Optional

from deep_coder.agent.task import Plan, Task, TaskStatus
from deep_coder.agent.worker import OnApprove, Worker
from deep_coder.client import DeepSeekClient, strip_dsml
from deep_coder.config import Config
from deep_coder.display import (
    PhaseSpinner,
    ReasoningStreamDisplay,
    TaskProgressDisplay,
    console,
    print_plan_summary,
)
from deep_coder.models import ModelRole
from deep_coder.prompts.system import get_orchestrator_prompt
from deep_coder.tools.base import ToolRegistry

OnPlanApproval = Optional[
    Callable[[str, list[dict[str, Any]]], Coroutine[Any, Any, str]]
]


def _make_assistant_msg(response: dict[str, Any]) -> dict[str, Any]:
    """Build an assistant message dict, preserving reasoning_content if present."""
    content = response.get("content")
    if content:
        content = strip_dsml(content)
    msg: dict[str, Any] = {"role": "assistant", "content": content}
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
        self.worker = Worker(client, tool_registry, config)
        self.conversation: list[dict[str, Any]] = []
        self._cwd: Optional[str] = None
        self._on_approve: OnApprove = None
        self._on_plan_approval: OnPlanApproval = None
        self._plan_revision_depth = 0

    def set_cwd(self, cwd: str) -> None:
        self._cwd = cwd
        self.worker.set_cwd(cwd)

    def set_approve_handler(self, handler: OnApprove) -> None:
        self._on_approve = handler

    def set_plan_approval_handler(self, handler: OnPlanApproval) -> None:
        self._on_plan_approval = handler

    _GREETING_PREFIXES = (
        "hi", "hello", "hey", "thanks", "thank you", "ok", "okay",
        "good morning", "good afternoon", "good evening", "good night",
        "你好", "谢谢", "早上好", "晚上好", "再见", "bye",
    )

    def _is_simple_greeting(self, message: str) -> bool:
        """Check if the message is a trivial greeting that doesn't need Pro."""
        text = message.strip().lower()
        if len(text) > 30:
            return False
        return any(text.startswith(g) for g in self._GREETING_PREFIXES)

    def _estimate_tokens(self) -> int:
        """Rough token estimate: ~4 chars per token."""
        return sum(len(m.get("content", "") or "") // 4 for m in self.conversation)

    async def process(
        self,
        user_message: str,
        on_token: Any = None,
        on_status: Any = None,
    ) -> str:
        self.conversation.append({"role": "user", "content": user_message})

        if self._estimate_tokens() > self.config.model.context_limit:
            n = len(self.conversation)
            console.print(f"  [dim]Auto-compacting conversation ({n} messages)...[/dim]")
            await self.compact()

        if self._is_simple_greeting(user_message):
            response = await self.client.collect_stream(
                messages=[
                    {"role": "system", "content": (
                        "You are Deep Coder, a helpful coding assistant. "
                        "Be brief and friendly."
                    )},
                    {"role": "user", "content": user_message},
                ],
                model_role=ModelRole.FLASH,
                on_token=on_token,
            )
            content = response.get("content") or ""
            self.conversation.append({"role": "assistant", "content": content})
            return content

        system_prompt = get_orchestrator_prompt(self._cwd)
        messages = [{"role": "system", "content": system_prompt}] + self.conversation

        reasoning_display = ReasoningStreamDisplay()
        try:
            await reasoning_display.start()
            response = await self.client.collect_stream(
                messages=messages,
                model_role=ModelRole.PRO,
                on_token=None,
                on_reasoning=reasoning_display.on_reasoning,
            )
            await reasoning_display.stop()
        except (KeyboardInterrupt, asyncio.CancelledError):
            await reasoning_display.stop(interrupted=True)
            raise KeyboardInterrupt("Interrupted during planning")

        content = strip_dsml(response.get("content") or "")

        plan = self._try_extract_plan(content)
        if plan and len(plan.tasks) > 0:
            plan_tasks_info = [
                {"id": t.id, "desc": t.description[:128] + ("..." if len(t.description) > 128 else ""), "deps": t.depends_on}
                for t in plan.tasks
            ]
            print_plan_summary(plan.description, plan_tasks_info)

            if self._on_plan_approval:
                approval = await self._on_plan_approval(
                    plan.description, plan_tasks_info,
                )
                if approval == "no":
                    self.conversation.append({
                        "role": "assistant",
                        "content": "(Plan rejected by user)",
                    })
                    return ""
                if approval != "yes":
                    self.conversation.append(
                        _make_assistant_msg(response),
                    )
                    if self._plan_revision_depth >= 3:
                        console.print(
                            "  [warning]Max revisions reached."
                            "[/warning]"
                        )
                        return ""
                    self._plan_revision_depth += 1
                    edit_msg = (
                        "The user wants to modify the plan. "
                        "Their feedback:\n"
                        f"{approval}\n\n"
                        "Please revise the plan accordingly."
                    )
                    try:
                        return await self.process(
                            edit_msg,
                            on_token=on_token,
                            on_status=on_status,
                        )
                    finally:
                        self._plan_revision_depth -= 1

            n = len(plan.tasks)
            try:
                await self._execute_plan_with_progress(plan, n)
            except (KeyboardInterrupt, asyncio.CancelledError):
                raise KeyboardInterrupt("Interrupted during execution")

            try:
                async with PhaseSpinner("verifying", "reviewing results"):
                    verification = await self._verify_results(plan, user_message)
            except (KeyboardInterrupt, asyncio.CancelledError):
                raise KeyboardInterrupt("Interrupted during verification")

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

    def _build_conversation_summary(self, max_exchanges: int = 5) -> str:
        """Build a compact summary of recent conversation for worker context."""
        recent = self.conversation[-(max_exchanges * 2):]
        parts: list[str] = []
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""
            if not content or role == "system":
                continue
            truncated = content[:300] + ("..." if len(content) > 300 else "")
            parts.append(f"[{role}]: {truncated}")
        return "\n".join(parts) if parts else ""

    async def _execute_plan_with_progress(self, plan: Plan, n_tasks: int = 0) -> None:
        """Execute plan with live progress display showing all task states."""
        detail = f"{n_tasks} task{'s' if n_tasks > 1 else ''}" if n_tasks else ""
        progress = TaskProgressDisplay(detail=detail)
        await progress.start(plan.tasks)

        max_concurrent = self.config.agent.max_workers
        approve_lock = asyncio.Lock()

        async def on_worker_status(task_id: str, status: str, detail: str) -> None:
            await progress.update(task_id, status, detail)

        async def on_approve_with_pause(tool_name: str, arguments: str) -> bool:
            if not self._on_approve:
                return True
            async with approve_lock:
                progress.pause()
                try:
                    return await self._on_approve(tool_name, arguments)
                finally:
                    progress.resume()

        async def on_tool_action(
            task_id: str, tool_name: str, args_summary: str,
            status: str, result_brief: str,
        ) -> None:
            progress.add_tool_action(
                task_id, tool_name, args_summary,
                status, result_brief,
            )

        try:
            while not plan.is_complete:
                ready = plan.get_ready_tasks()
                if not ready:
                    break

                batch = ready[:max_concurrent]
                completed_tasks = {t.id: t for t in plan.tasks if t.status == TaskStatus.COMPLETED}
                for task in batch:
                    if task.depends_on:
                        dep_results = []
                        for dep_id in task.depends_on:
                            dep = completed_tasks.get(dep_id)
                            if dep and dep.result:
                                dep_results.append(f"[{dep_id}]: {dep.result[:500]}")
                        if dep_results:
                            task.context += "\n\nCompleted dependency results:\n" + "\n".join(dep_results)
                coros = [
                    self._run_worker(
                        task, on_worker_status=on_worker_status,
                        on_approve=on_approve_with_pause,
                        on_tool_action=on_tool_action,
                    )
                    for task in batch
                ]
                await asyncio.gather(*coros)

            failed_tasks = [t for t in plan.tasks if t.status == TaskStatus.FAILED and t.retry_count == 0]
            if failed_tasks:
                for task in failed_tasks:
                    task.mark_retrying()
                    task.context += f"\n\nPrevious attempt failed with error: {task.error}\nPlease try a different approach."
                    await on_worker_status(task.id, "running", "retrying")
                retry_coros = [
                    self._run_worker(
                        task, on_worker_status=on_worker_status,
                        on_approve=on_approve_with_pause,
                        on_tool_action=on_tool_action,
                    )
                    for task in failed_tasks
                ]
                await asyncio.gather(*retry_coros)
        finally:
            await progress.stop()

        completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)
        retried = sum(1 for t in plan.tasks if t.retry_count > 0 and t.status == TaskStatus.COMPLETED)
        summary_parts = [f"[green]{completed} completed[/green]"]
        if retried:
            summary_parts.append(f"[yellow]{retried} recovered[/yellow]")
        if failed:
            summary_parts.append(f"[red]{failed} failed[/red]")
        console.print(f"  [dim]Results:[/dim] {', '.join(summary_parts)}\n")

    async def _run_worker(
        self,
        task: Task,
        on_status: Any = None,
        on_worker_status: Any = None,
        on_approve: OnApprove = None,
        on_tool_action: Any = None,
    ) -> None:
        try:
            await self.worker.execute(
                task,
                on_status=on_status,
                on_worker_status=on_worker_status,
                on_approve=on_approve or self._on_approve,
                on_tool_action=on_tool_action,
                conversation_summary=self._build_conversation_summary(),
            )
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
