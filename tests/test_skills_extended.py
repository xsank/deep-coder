"""Extended tests for skills — base class methods, skill context, skill registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from deep_coder.skills.base import SkillContext
from deep_coder.skills.explain import ExplainSkill
from deep_coder.skills.fix import FixSkill
from deep_coder.skills.memory import MemorySkill, RememberSkill
from deep_coder.skills.pr import PRSkill
from deep_coder.skills.think import ThinkSkill


class TestSkillContext:
    def test_creation(self):
        ctx = SkillContext(
            orchestrator=MagicMock(),
            client=MagicMock(),
            config=MagicMock(),
            status_panel=None,
            cwd="/tmp",
        )
        assert ctx.cwd == "/tmp"
        assert ctx.status_panel is None


class TestSkillRunGit:
    async def test_run_git(self):
        skill = FixSkill()
        code, stdout, stderr = await skill._run_git("--version")
        assert code == 0
        assert "git version" in stdout

    async def test_run_shell(self):
        skill = FixSkill()
        code, stdout, stderr = await skill._run_shell("echo hello")
        assert code == 0
        assert "hello" in stdout

    async def test_run_shell_timeout(self):
        skill = FixSkill()
        code, stdout, stderr = await skill._run_shell("sleep 10", timeout=1)
        assert code == 1
        assert "timed out" in stderr.lower()


class TestFixSkillExecute:
    @patch("deep_coder.skills.fix.print_error")
    async def test_empty_arg(self, mock_print_error):
        skill = FixSkill()
        ctx = SkillContext(
            orchestrator=MagicMock(),
            client=MagicMock(),
            config=MagicMock(),
            status_panel=None,
            cwd="/tmp",
        )
        await skill.execute("", ctx)
        mock_print_error.assert_called_once()
        assert "provide" in mock_print_error.call_args[0][0].lower()


class TestThinkSkillExecute:
    @patch("deep_coder.skills.think.print_error")
    async def test_empty_arg(self, mock_print_error):
        skill = ThinkSkill()
        ctx = SkillContext(
            orchestrator=MagicMock(),
            client=MagicMock(),
            config=MagicMock(),
            status_panel=None,
            cwd="/tmp",
        )
        await skill.execute("", ctx)
        mock_print_error.assert_called_once()
        assert "provide" in mock_print_error.call_args[0][0].lower()


class TestRememberSkill:
    def test_properties(self):
        skill = RememberSkill()
        assert skill.name == "/remember"
        assert "/remember" in skill.usage

    @patch("deep_coder.skills.memory.print_error")
    async def test_empty_arg(self, mock_print_error):
        skill = RememberSkill()
        ctx = SkillContext(
            orchestrator=MagicMock(),
            client=MagicMock(),
            config=MagicMock(),
            status_panel=None,
            cwd="/tmp",
        )
        await skill.execute("", ctx)
        mock_print_error.assert_called_once()


class TestMemorySkill:
    def test_properties(self):
        skill = MemorySkill()
        assert skill.name == "/memory"
        assert "/memory" in skill.usage


class TestExplainSkill:
    def test_properties(self):
        skill = ExplainSkill()
        assert skill.name == "/explain"
        assert "explain" in skill.description.lower()


class TestPRSkill:
    def test_properties(self):
        skill = PRSkill()
        assert skill.name == "/pr"
