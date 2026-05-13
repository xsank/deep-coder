"""Extended tests for server.py — handler methods with mocked dependencies."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

aiohttp = pytest.importorskip("aiohttp")

from deep_coder.server import DeepCoderServer  # noqa: E402


@pytest.fixture
def server():
    with (
        patch("deep_coder.server.DeepSeekClient") as mock_client_cls,
        patch("deep_coder.server.create_default_registry"),
        patch("deep_coder.server.Orchestrator") as mock_orch_cls,
    ):
        mock_client = MagicMock()
        mock_client.usage = MagicMock(
            total_requests=5,
            total_cost=0.01,
            pro_prompt_tokens=100,
            pro_completion_tokens=50,
            flash_prompt_tokens=200,
            flash_completion_tokens=100,
        )
        mock_client_cls.return_value = mock_client

        mock_orch = MagicMock()
        mock_orch.process = AsyncMock(return_value="response text")
        mock_orch.clear_history = MagicMock()
        mock_orch.compact = AsyncMock(return_value="Compacted")
        mock_orch.set_cwd = MagicMock()
        mock_orch.set_approve_handler = MagicMock()
        mock_orch.set_plan_approval_handler = MagicMock()
        mock_orch_cls.return_value = mock_orch

        config = MagicMock()
        srv = DeepCoderServer(config)
        srv._client = mock_client
        srv._orchestrator = mock_orch
        yield srv


class TestHealthHandler:
    async def test_health_response(self, server):
        request = MagicMock()
        response = await server._health_handler(request)
        assert response.status == 200
        body = json.loads(response.body)
        assert body["status"] == "ok"
        assert body["requests"] == 5


class TestHandleCommand:
    async def test_clear_command(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._handle_command(ws, "/clear")
        ws.send_json.assert_called()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "done"
        assert "cleared" in call_data["content"].lower()

    async def test_cost_command(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._handle_command(ws, "/cost")
        ws.send_json.assert_called()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "done"
        assert "Pro:" in call_data["content"]

    async def test_compact_command(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._handle_command(ws, "/compact")
        ws.send_json.assert_called()

    async def test_unknown_command(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._handle_command(ws, "/unknown")
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "error"


class TestHandleChat:
    async def test_empty_message(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._handle_chat(ws, "")
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "error"
        assert "empty" in call_data["message"].lower()

    async def test_successful_chat(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._handle_chat(ws, "hello")
        calls = [c[0][0] for c in ws.send_json.call_args_list]
        types = [c["type"] for c in calls]
        assert "cost" in types
        assert "done" in types

    async def test_chat_exception(self, server):
        ws = AsyncMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        server._orchestrator.process = AsyncMock(side_effect=RuntimeError("boom"))
        await server._handle_chat(ws, "hello")
        calls = [c[0][0] for c in ws.send_json.call_args_list]
        error_calls = [c for c in calls if c["type"] == "error"]
        assert len(error_calls) > 0
        assert "boom" in error_calls[0]["message"]


class TestCancelAndResolve:
    def test_cancel_no_task(self, server):
        server._cancel_current()

    def test_cancel_running_task(self, server):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()
        server._current_task = mock_task
        server._cancel_current()
        mock_task.cancel.assert_called_once()

    def test_resolve_approval(self, server):
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        server._approval_futures["req1"] = future
        server._resolve_approval("req1", True)
        assert future.result() is True
        loop.close()

    def test_resolve_approval_missing(self, server):
        server._resolve_approval("nonexistent", True)

    def test_resolve_plan_approval(self, server):
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        server._plan_approval_futures["req2"] = future
        server._resolve_plan_approval("req2", "yes")
        assert future.result() == "yes"
        loop.close()

    async def test_send_closed_ws(self, server):
        ws = MagicMock()
        ws.closed = True
        ws.send_json = AsyncMock()
        await server._send(ws, {"type": "test"})
        ws.send_json.assert_not_called()

    async def test_send_open_ws(self, server):
        ws = MagicMock()
        ws.closed = False
        ws.send_json = AsyncMock()
        await server._send(ws, {"type": "test"})
        ws.send_json.assert_called_once()
