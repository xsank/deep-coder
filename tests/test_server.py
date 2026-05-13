"""Tests for server.py — DeepCoderServer basics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

aiohttp = pytest.importorskip("aiohttp")

from deep_coder.config import Config, ModelConfig  # noqa: E402
from deep_coder.server import DeepCoderServer  # noqa: E402


class TestDeepCoderServer:
    @pytest.fixture
    def config(self):
        return Config(model=ModelConfig(api_key="test"))

    def test_init(self, config):
        server = DeepCoderServer(config, host="127.0.0.1", port=9120)
        assert server.host == "127.0.0.1"
        assert server.port == 9120
        assert server._current_task is None

    def test_init_custom_port(self, config):
        server = DeepCoderServer(config, port=8080)
        assert server.port == 8080

    async def test_health_handler(self, config):
        server = DeepCoderServer(config)
        request = MagicMock()
        response = await server._health_handler(request)
        import json

        data = json.loads(response.body)
        assert data["status"] == "ok"
        assert data["requests"] == 0
        assert data["cost"] == 0

    def test_cancel_no_task(self, config):
        server = DeepCoderServer(config)
        server._cancel_current()  # should not raise

    def test_cancel_completed_task(self, config):
        server = DeepCoderServer(config)
        task = MagicMock()
        task.done.return_value = True
        server._current_task = task
        server._cancel_current()
        task.cancel.assert_not_called()

    def test_cancel_running_task(self, config):
        server = DeepCoderServer(config)
        task = MagicMock()
        task.done.return_value = False
        server._current_task = task
        server._cancel_current()
        task.cancel.assert_called_once()

    def test_resolve_approval(self, config):
        import asyncio

        server = DeepCoderServer(config)
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        server._approval_futures["req1"] = future
        server._resolve_approval("req1", True)
        assert future.result() is True
        loop.close()

    def test_resolve_approval_unknown_id(self, config):
        server = DeepCoderServer(config)
        server._resolve_approval("unknown", True)  # should not raise

    def test_resolve_plan_approval(self, config):
        import asyncio

        server = DeepCoderServer(config)
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        server._plan_approval_futures["req1"] = future
        server._resolve_plan_approval("req1", "yes")
        assert future.result() == "yes"
        loop.close()

    async def test_handle_command_clear(self, config):
        server = DeepCoderServer(config)
        ws = AsyncMock()
        ws.closed = False
        await server._handle_command(ws, "/clear")
        ws.send_json.assert_called()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "done"
        assert "cleared" in call_data["content"].lower()

    async def test_handle_command_cost(self, config):
        server = DeepCoderServer(config)
        ws = AsyncMock()
        ws.closed = False
        await server._handle_command(ws, "/cost")
        ws.send_json.assert_called()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "done"

    async def test_handle_command_unknown(self, config):
        server = DeepCoderServer(config)
        ws = AsyncMock()
        ws.closed = False
        await server._handle_command(ws, "/unknown")
        ws.send_json.assert_called()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "error"

    async def test_handle_chat_empty(self, config):
        server = DeepCoderServer(config)
        ws = AsyncMock()
        ws.closed = False
        await server._handle_chat(ws, "")
        ws.send_json.assert_called()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "error"
        assert "empty" in call_data["message"].lower()

    async def test_send_closed_ws(self, config):
        server = DeepCoderServer(config)
        ws = AsyncMock()
        ws.closed = True
        await server._send(ws, {"type": "test"})
        ws.send_json.assert_not_called()
