"""Tests for agent/worker.py — _make_assistant_msg, auto-approve, execute."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from deep_coder.agent.task import Task, TaskStatus
from deep_coder.agent.worker import Worker, _make_assistant_msg
from deep_coder.client import DeepSeekClient
from deep_coder.config import AgentConfig, Config, ModelConfig
from deep_coder.tools.base import Tool, ToolRegistry, ToolResult


class TestWorkerMakeAssistantMsg:
    def test_basic(self):
        msg = _make_assistant_msg({"content": "hello"})
        assert msg["role"] == "assistant"
        assert msg["content"] == "hello"

    def test_with_reasoning(self):
        msg = _make_assistant_msg({"content": "x", "reasoning_content": "thinking"})
        assert msg["reasoning_content"] == "thinking"

    def test_with_tool_calls(self):
        msg = _make_assistant_msg({"content": None, "tool_calls": [{"id": "tc1"}]})
        assert msg["tool_calls"] == [{"id": "tc1"}]

    def test_no_extras(self):
        msg = _make_assistant_msg({"content": "ok"})
        assert "reasoning_content" not in msg
        assert "tool_calls" not in msg


class DummyReadTool(Tool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read a file"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.ok("file content")


class DummyWriteTool(Tool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write a file"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        }

    @property
    def is_read_only(self) -> bool:
        return False

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.ok("written")


class TestShouldAutoApprove:
    @pytest.fixture
    def make_worker(self):
        def _make(policy="default", auto_approve_reads=True):
            config = Config(
                model=ModelConfig(api_key="test"),
                agent=AgentConfig(auto_approve_reads=auto_approve_reads),
            )
            config.approval_policy = policy
            client = DeepSeekClient(config)
            registry = ToolRegistry()
            return Worker(client, registry, config)

        return _make

    def test_auto_policy(self, make_worker):
        worker = make_worker(policy="auto")
        assert worker._should_auto_approve(DummyReadTool()) is True
        assert worker._should_auto_approve(DummyWriteTool()) is True

    def test_none_policy(self, make_worker):
        worker = make_worker(policy="none")
        assert worker._should_auto_approve(DummyReadTool()) is False
        assert worker._should_auto_approve(DummyWriteTool()) is False

    def test_default_reads_auto(self, make_worker):
        worker = make_worker(policy="default", auto_approve_reads=True)
        assert worker._should_auto_approve(DummyReadTool()) is True
        assert worker._should_auto_approve(DummyWriteTool()) is False

    def test_default_reads_not_auto(self, make_worker):
        worker = make_worker(policy="default", auto_approve_reads=False)
        assert worker._should_auto_approve(DummyReadTool()) is False
        assert worker._should_auto_approve(DummyWriteTool()) is False


class TestWorkerSetCwd:
    def test_set_cwd(self):
        config = Config()
        client = DeepSeekClient(config)
        registry = ToolRegistry()
        worker = Worker(client, registry, config)
        worker.set_cwd("/some/path")
        assert worker._cwd == "/some/path"


class TestWorkerExecute:
    @pytest.fixture
    def setup(self):
        config = Config(model=ModelConfig(api_key="test"))
        config.approval_policy = "auto"
        client = DeepSeekClient(config)
        registry = ToolRegistry()
        registry.register(DummyReadTool())
        worker = Worker(client, registry, config)
        worker.set_cwd("/tmp")
        return worker, client

    @patch("deep_coder.agent.worker.print_file_diff")
    async def test_execute_no_tools(self, mock_diff, setup):
        worker, client = setup
        task = Task(id="t1", description="Say hello")

        client.collect_stream = AsyncMock(return_value={"content": "Hello!", "tool_calls": None})

        result = await worker.execute(task)
        assert result == "Hello!"
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "Hello!"

    @patch("deep_coder.agent.worker.print_file_diff")
    async def test_execute_with_tool_call(self, mock_diff, setup):
        worker, client = setup
        task = Task(id="t1", description="Read a file")

        call_count = 0

        async def mock_collect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "tc_1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"file_path": "/tmp/test.py"}',
                            },
                        }
                    ],
                }
            return {"content": "File contains test code.", "tool_calls": None}

        client.collect_stream = AsyncMock(side_effect=mock_collect)

        result = await worker.execute(task)
        assert "File contains test code" in result
        assert task.status == TaskStatus.COMPLETED

    @patch("deep_coder.agent.worker.print_file_diff")
    async def test_execute_max_iterations(self, mock_diff, setup):
        worker, client = setup
        task = Task(id="t1", description="Infinite loop")

        client.collect_stream = AsyncMock(
            return_value={
                "content": None,
                "tool_calls": [
                    {
                        "id": "tc_1",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"file_path": "/tmp/test.py"}',
                        },
                    }
                ],
            }
        )

        result = await worker.execute(task)
        assert "max iterations" in result.lower()
        assert task.status == TaskStatus.FAILED

    @patch("deep_coder.agent.worker.print_file_diff")
    async def test_execute_with_status_callbacks(self, mock_diff, setup):
        worker, client = setup
        task = Task(id="t1", description="Test callbacks")

        client.collect_stream = AsyncMock(return_value={"content": "Done", "tool_calls": None})

        statuses = []

        async def on_worker_status(task_id, status, detail):
            statuses.append((task_id, status, detail))

        await worker.execute(task, on_worker_status=on_worker_status)
        assert any(s[1] == "running" for s in statuses)
        assert any(s[1] == "completed" for s in statuses)

    @patch("deep_coder.agent.worker.print_file_diff")
    async def test_execute_tool_denied(self, mock_diff, setup):
        worker, client = setup

        config = worker.config
        config.approval_policy = "default"
        config.agent.auto_approve_reads = False

        registry = ToolRegistry()
        registry.register(DummyWriteTool())
        worker.tool_registry = registry

        task = Task(id="t1", description="Write file")

        call_count = 0

        async def mock_collect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "tc_1",
                            "function": {
                                "name": "write_file",
                                "arguments": '{"file_path": "/tmp/x.py", "content": ""}',
                            },
                        }
                    ],
                }
            return {"content": "Operation denied by user.", "tool_calls": None}

        client.collect_stream = AsyncMock(side_effect=mock_collect)

        async def deny_all(tool_name, arguments):
            return False

        await worker.execute(task, on_approve=deny_all)
        assert task.status == TaskStatus.COMPLETED

    @patch("deep_coder.agent.worker.print_file_diff")
    async def test_execute_dsml_stripped(self, mock_diff, setup):
        worker, client = setup
        task = Task(id="t1", description="Test")

        client.collect_stream = AsyncMock(
            return_value={
                "content": "before<DSML>hidden</DSML>after",
                "tool_calls": None,
            }
        )

        result = await worker.execute(task)
        assert "DSML" not in result
        assert "beforeafter" in result
