"""Tests for Skill._stream_to_console."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deep_coder.skills.base import Skill, SkillContext


class DummySkill(Skill):
    @property
    def name(self) -> str:
        return "/dummy"

    @property
    def description(self) -> str:
        return "Dummy skill"

    @property
    def usage(self) -> str:
        return "/dummy"

    async def execute(self, arg: str, ctx: SkillContext) -> None:
        pass


@pytest.fixture
def ctx():
    return SkillContext(
        orchestrator=MagicMock(),
        client=MagicMock(),
        config=MagicMock(),
        status_panel=None,
        cwd="/tmp",
    )


class TestStreamToConsole:
    @patch("deep_coder.display.StreamPrinter")
    @patch("deep_coder.display.print_response")
    async def test_without_tools(self, mock_print_response, mock_printer_cls, ctx):
        mock_printer = MagicMock()
        mock_printer.on_token = AsyncMock()
        mock_printer.finish = MagicMock()
        mock_printer.get_content.return_value = ""
        mock_printer_cls.return_value = mock_printer

        ctx.client.collect_stream = AsyncMock(return_value={"content": "AI response"})

        skill = DummySkill()
        result = await skill._stream_to_console(ctx, "test prompt")
        assert result == "AI response"
        mock_print_response.assert_called_once_with("AI response")

    @patch("deep_coder.display.StreamPrinter")
    async def test_with_tools(self, mock_printer_cls, ctx):
        mock_printer = MagicMock()
        mock_printer.on_token = AsyncMock()
        mock_printer.finish = MagicMock()
        mock_printer.get_content.return_value = "streamed content"
        mock_printer_cls.return_value = mock_printer

        ctx.orchestrator.process = AsyncMock(return_value="tool result")

        skill = DummySkill()
        result = await skill._stream_to_console(ctx, "test prompt", use_tools=True)
        assert result == "tool result"
        ctx.orchestrator.process.assert_called_once()

    @patch("deep_coder.display.StreamPrinter")
    async def test_with_status_panel(self, mock_printer_cls):
        mock_printer = MagicMock()
        mock_printer.on_token = AsyncMock()
        mock_printer.finish = MagicMock()
        mock_printer.get_content.return_value = "content"
        mock_printer_cls.return_value = mock_printer

        status_panel = MagicMock()
        status_panel.refresh = MagicMock()

        ctx = SkillContext(
            orchestrator=MagicMock(),
            client=MagicMock(),
            config=MagicMock(),
            status_panel=status_panel,
            cwd="/tmp",
        )
        ctx.client.collect_stream = AsyncMock(return_value={"content": "resp"})

        skill = DummySkill()
        await skill._stream_to_console(ctx, "test")
        status_panel.refresh.assert_called_once_with(force=True)
