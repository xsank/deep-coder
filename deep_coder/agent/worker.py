"""Worker agent — executes a single task using Flash model with tool calls."""

from __future__ import annotations

from typing import Any, Callable, Coroutine, Optional

from deep_coder.agent.task import Task
from deep_coder.client import DeepSeekClient, strip_dsml
from deep_coder.config import Config
from deep_coder.display import print_file_diff, summarize_tool_args, summarize_tool_result
from deep_coder.models import ModelRole
from deep_coder.prompts.system import get_worker_prompt
from deep_coder.tools.base import Tool, ToolRegistry

OnWorkerStatus = Optional[Callable[[str, str, str], Coroutine[Any, Any, None]]]
OnApprove = Optional[Callable[[str, str], Coroutine[Any, Any, bool]]]
OnToolAction = Optional[
    Callable[[str, str, str, str, str], Coroutine[Any, Any, None]]
]


def _make_assistant_msg(response: dict[str, Any]) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": response.get("content")}
    if response.get("reasoning_content"):
        msg["reasoning_content"] = response["reasoning_content"]
    if response.get("tool_calls"):
        msg["tool_calls"] = response["tool_calls"]
    return msg


class Worker:
    """Executes a single subtask using DeepSeek V4 Flash with tool access."""

    def __init__(self, client: DeepSeekClient, tool_registry: ToolRegistry, config: Config) -> None:
        self.client = client
        self.tool_registry = tool_registry
        self.config = config
        self._cwd: str | None = None

    def set_cwd(self, cwd: str) -> None:
        self._cwd = cwd

    def _should_auto_approve(self, tool: Tool) -> bool:
        """Check if a tool call can be auto-approved based on config policy."""
        policy = self.config.approval_policy
        if policy == "auto":
            return True
        if policy == "none":
            return False
        if self.config.agent.auto_approve_reads and tool.is_read_only:
            return True
        return False

    async def execute(
        self,
        task: Task,
        on_status: Any = None,
        on_worker_status: OnWorkerStatus = None,
        on_approve: OnApprove = None,
        on_tool_action: OnToolAction = None,
        conversation_summary: str = "",
    ) -> str:
        task.mark_running()
        if on_status:
            await on_status(task, "running")
        if on_worker_status:
            await on_worker_status(task.id, "running", "starting")

        system_prompt = get_worker_prompt(
            task.description, task.context,
            cwd=self._cwd, conversation_summary=conversation_summary,
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.description},
        ]
        tools = self.tool_registry.to_openai_tools()

        max_iterations = 15
        for iteration in range(max_iterations):
            if on_worker_status:
                detail = f"thinking ({iteration + 1}/{max_iterations})"
                await on_worker_status(task.id, "running", detail)

            async def on_reasoning(text: str) -> None:
                if on_worker_status:
                    truncated = text.strip().replace("\n", " ")[:60]
                    if truncated:
                        await on_worker_status(task.id, "running", f"thinking: {truncated}")

            response = await self.client.collect_stream(
                messages=messages,
                model_role=ModelRole.FLASH,
                tools=tools if tools else None,
                on_reasoning=on_reasoning,
            )

            if response.get("tool_calls"):
                messages.append(_make_assistant_msg(response))
                for tc in response["tool_calls"]:
                    fn = tc["function"]
                    tool_name = fn["name"]

                    args_summary = summarize_tool_args(
                        tool_name, fn["arguments"],
                    )
                    display_detail = tool_name
                    if args_summary:
                        display_detail += f": {args_summary}"
                    if on_worker_status:
                        await on_worker_status(
                            task.id, "running", display_detail,
                        )
                    if on_status:
                        await on_status(task, f"tool:{tool_name}")
                    if on_tool_action:
                        await on_tool_action(
                            task.id, tool_name, args_summary,
                            "start", "",
                        )

                    tool_obj = self.tool_registry.get(tool_name)
                    if tool_obj and tool_obj.requires_approval:
                        approved = self._should_auto_approve(tool_obj)
                        if not approved and on_approve:
                            approved = await on_approve(
                                tool_name, fn["arguments"],
                            )
                        if not approved:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": "User denied this operation.",
                            })
                            if on_tool_action:
                                await on_tool_action(
                                    task.id, tool_name,
                                    args_summary, "failed", "denied",
                                )
                            continue

                    result = await self.tool_registry.dispatch(
                        tool_name, fn["arguments"],
                    )
                    if result.success and result.metadata and "old_content" in result.metadata:
                        print_file_diff(
                            result.metadata["file_path"],
                            result.metadata["old_content"],
                            result.metadata["new_content"],
                        )
                    brief = summarize_tool_result(
                        tool_name, result.content, result.success,
                    )
                    if on_tool_action:
                        st = "done" if result.success else "failed"
                        await on_tool_action(
                            task.id, tool_name, args_summary,
                            st, brief,
                        )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result.content,
                    })
            else:
                content = strip_dsml(response.get("content") or "")
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
