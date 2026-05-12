"""WebSocket server exposing Deep Coder orchestrator for VS Code extension."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from aiohttp import web

from deep_coder.agent.orchestrator import Orchestrator
from deep_coder.client import DeepSeekClient
from deep_coder.config import Config
from deep_coder.tools.base import create_default_registry


class DeepCoderServer:
    """WebSocket server wrapping the orchestrator for IDE integration."""

    def __init__(self, config: Config, host: str = "127.0.0.1", port: int = 9120) -> None:
        self.config = config
        self.host = host
        self.port = port
        self._app = web.Application()
        self._app.router.add_get("/ws", self._ws_handler)
        self._app.router.add_get("/health", self._health_handler)
        self._client = DeepSeekClient(config)
        self._registry = create_default_registry()
        self._orchestrator = Orchestrator(self._client, config, self._registry)
        self._orchestrator.set_cwd(os.getcwd())
        self._current_task: asyncio.Task[Any] | None = None
        self._approval_futures: dict[str, asyncio.Future[bool]] = {}

    async def _health_handler(self, request: web.Request) -> web.Response:
        usage = self._client.usage
        return web.json_response({
            "status": "ok",
            "requests": usage.total_requests,
            "cost": round(usage.total_cost, 6),
        })

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for raw_msg in ws:
            if raw_msg.type != web.WSMsgType.TEXT:
                continue
            try:
                msg = json.loads(raw_msg.data)
            except json.JSONDecodeError:
                await self._send(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "chat":
                await self._handle_chat(ws, msg.get("message", ""))
            elif msg_type == "command":
                await self._handle_command(ws, msg.get("command", ""))
            elif msg_type == "cancel":
                self._cancel_current()
            elif msg_type == "approval_response":
                self._resolve_approval(msg.get("id", ""), msg.get("approved", False))
            else:
                await self._send(ws, {"type": "error", "message": f"Unknown type: {msg_type}"})

        return ws

    async def _handle_chat(self, ws: web.WebSocketResponse, message: str) -> None:
        if not message.strip():
            await self._send(ws, {"type": "error", "message": "Empty message"})
            return

        async def on_token(token: str) -> None:
            await self._send(ws, {"type": "token", "content": token})

        async def on_reasoning(token: str) -> None:
            await self._send(ws, {"type": "planning", "reasoning": token})

        async def on_approve(tool_name: str, arguments: str) -> bool:
            req_id = uuid.uuid4().hex[:8]
            future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
            self._approval_futures[req_id] = future
            await self._send(ws, {
                "type": "approval",
                "id": req_id,
                "tool": tool_name,
                "arguments": arguments,
            })
            try:
                return await asyncio.wait_for(future, timeout=300)
            except asyncio.TimeoutError:
                return False
            finally:
                self._approval_futures.pop(req_id, None)

        self._orchestrator.set_approve_handler(on_approve)

        original_process = self._orchestrator.process

        async def patched_process() -> str:
            return await original_process(message, on_token=on_token)

        try:
            self._current_task = asyncio.create_task(patched_process())
            result = await self._current_task

            usage = self._client.usage
            await self._send(ws, {
                "type": "cost",
                "pro_tokens": usage.pro_prompt_tokens + usage.pro_completion_tokens,
                "flash_tokens": usage.flash_prompt_tokens + usage.flash_completion_tokens,
                "cost": round(usage.total_cost, 6),
            })
            await self._send(ws, {"type": "done", "content": result})
        except (KeyboardInterrupt, asyncio.CancelledError):
            await self._send(ws, {"type": "error", "message": "Cancelled"})
        except Exception as e:
            await self._send(ws, {"type": "error", "message": str(e)})
        finally:
            self._current_task = None

    async def _handle_command(self, ws: web.WebSocketResponse, command: str) -> None:
        if command == "/clear":
            self._orchestrator.clear_history()
            await self._send(ws, {"type": "done", "content": "History cleared."})
        elif command == "/cost":
            u = self._client.usage
            await self._send(ws, {
                "type": "done",
                "content": (
                    f"Pro: {u.pro_prompt_tokens + u.pro_completion_tokens:,} tokens, "
                    f"Flash: {u.flash_prompt_tokens + u.flash_completion_tokens:,} tokens, "
                    f"Cost: ${u.total_cost:.4f}"
                ),
            })
        elif command.startswith("/compact"):
            async def on_token(t: str) -> None:
                await self._send(ws, {"type": "token", "content": t})
            summary = await self._orchestrator.compact(on_token=on_token)
            await self._send(ws, {"type": "done", "content": summary})
        else:
            await self._send(ws, {
                "type": "error",
                "message": f"Unknown command: {command}",
            })

    def _cancel_current(self) -> None:
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    def _resolve_approval(self, req_id: str, approved: bool) -> None:
        future = self._approval_futures.get(req_id)
        if future and not future.done():
            future.set_result(approved)

    async def _send(self, ws: web.WebSocketResponse, data: dict[str, Any]) -> None:
        if not ws.closed:
            await ws.send_json(data)

    def run(self) -> None:
        print(f"Deep Coder server listening on ws://{self.host}:{self.port}/ws")
        web.run_app(self._app, host=self.host, port=self.port, print=None)


def run_server(config: Config, host: str = "127.0.0.1", port: int = 9120) -> None:
    server = DeepCoderServer(config, host, port)
    server.run()
