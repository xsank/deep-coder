"""Tests for skill execute() methods — explain, review, pr, commit, test_skill."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deep_coder.skills.base import SkillContext
from deep_coder.skills.commit import CommitSkill
from deep_coder.skills.explain import ExplainSkill
from deep_coder.skills.pr import PRSkill
from deep_coder.skills.review import ReviewSkill
from deep_coder.skills.test_skill import TestSkill


@pytest.fixture
def cwd():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def ctx(cwd):
    return SkillContext(
        orchestrator=MagicMock(),
        client=MagicMock(),
        config=MagicMock(),
        status_panel=None,
        cwd=cwd,
    )


class TestExplainSkillExecute:
    async def test_explain_project_with_coder_md(self, ctx, cwd):
        coder_md = os.path.join(cwd, "CODER.md")
        with open(coder_md, "w") as f:
            f.write("# Project\nThis is a test project.")

        skill = ExplainSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("", ctx)
            skill._stream_to_console.assert_called_once()
            call_args = skill._stream_to_console.call_args
            assert "CODER.md" in call_args[0][1]

    async def test_explain_project_no_coder_md(self, ctx):
        skill = ExplainSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("", ctx)
            skill._stream_to_console.assert_called_once()
            call_args = skill._stream_to_console.call_args
            assert call_args[1].get("use_tools") is True

    async def test_explain_file(self, ctx, cwd):
        test_file = os.path.join(cwd, "example.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    return 'world'\n")

        skill = ExplainSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("example.py", ctx)
            skill._stream_to_console.assert_called_once()
            prompt = skill._stream_to_console.call_args[0][1]
            assert "example.py" in prompt
            assert "hello" in prompt

    async def test_explain_file_with_line_range(self, ctx, cwd):
        test_file = os.path.join(cwd, "example.py")
        with open(test_file, "w") as f:
            f.write("\n".join(f"line {i}" for i in range(50)))

        skill = ExplainSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("example.py:5-10", ctx)
            skill._stream_to_console.assert_called_once()

    async def test_explain_file_with_single_line(self, ctx, cwd):
        test_file = os.path.join(cwd, "example.py")
        with open(test_file, "w") as f:
            f.write("\n".join(f"line {i}" for i in range(50)))

        skill = ExplainSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("example.py:5", ctx)
            skill._stream_to_console.assert_called_once()

    @patch("deep_coder.skills.explain.print_error")
    async def test_explain_file_not_found(self, mock_error, ctx):
        skill = ExplainSkill()
        await skill.execute("nonexistent.py", ctx)
        mock_error.assert_called_once()
        assert "not found" in mock_error.call_args[0][0].lower()

    @patch("deep_coder.skills.explain.print_error")
    async def test_explain_invalid_line_range(self, mock_error, ctx, cwd):
        test_file = os.path.join(cwd, "example.py")
        with open(test_file, "w") as f:
            f.write("x")

        skill = ExplainSkill()
        await skill.execute("example.py:abc-def", ctx)
        mock_error.assert_called_once()

    @patch("deep_coder.skills.explain.print_error")
    async def test_explain_invalid_single_line(self, mock_error, ctx, cwd):
        test_file = os.path.join(cwd, "example.py")
        with open(test_file, "w") as f:
            f.write("x")

        skill = ExplainSkill()
        await skill.execute("example.py:abc", ctx)
        mock_error.assert_called_once()

    async def test_explain_large_file_truncated(self, ctx, cwd):
        test_file = os.path.join(cwd, "big.py")
        with open(test_file, "w") as f:
            f.write("\n".join(f"line {i}" for i in range(300)))

        skill = ExplainSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("big.py", ctx)
            prompt = skill._stream_to_console.call_args[0][1]
            assert "more lines" in prompt


class TestReviewSkillExecute:
    async def test_review_file(self, ctx, cwd):
        test_file = os.path.join(cwd, "example.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    return 'world'\n")

        skill = ReviewSkill()
        with patch.object(skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"):
            await skill.execute("example.py", ctx)
            prompt = skill._stream_to_console.call_args[0][1]
            assert "Code Review" in prompt
            assert "hello" in prompt

    @patch("deep_coder.skills.review.print_error")
    async def test_review_file_not_found(self, mock_error, ctx):
        skill = ReviewSkill()
        await skill.execute("nonexistent.py", ctx)
        mock_error.assert_called_once()

    async def test_review_staged_changes(self, ctx):
        skill = ReviewSkill()
        with patch.object(
            skill,
            "_run_git",
            new_callable=AsyncMock,
            return_value=(0, "diff content here", ""),
        ):
            with patch.object(
                skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"
            ):
                await skill.execute("staged", ctx)
                prompt = skill._stream_to_console.call_args[0][1]
                assert "diff" in prompt.lower()

    @patch("deep_coder.skills.review.print_warning")
    async def test_review_no_changes(self, mock_warning, ctx):
        skill = ReviewSkill()
        with patch.object(skill, "_run_git", new_callable=AsyncMock, return_value=(0, "", "")):
            await skill.execute("", ctx)
            mock_warning.assert_called_once()
            assert "no staged" in mock_warning.call_args[0][0].lower()

    async def test_review_unstaged_fallback(self, ctx):
        skill = ReviewSkill()
        call_count = 0

        async def mock_run_git(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (0, "", "")
            return (0, "unstaged diff", "")

        with patch.object(skill, "_run_git", side_effect=mock_run_git):
            with patch.object(
                skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"
            ):
                await skill.execute("", ctx)
                skill._stream_to_console.assert_called_once()


class TestPRSkillExecute:
    async def test_pr_success(self, ctx):
        skill = PRSkill()
        git_calls = [
            (0, "feature-branch", ""),
            (0, "abc123 commit msg", ""),
            (0, "file.py | 5 ++--", ""),
            (0, "diff content", ""),
        ]
        call_idx = 0

        async def mock_run_git(*args, **kwargs):
            nonlocal call_idx
            result = git_calls[call_idx]
            call_idx += 1
            return result

        with patch.object(skill, "_run_git", side_effect=mock_run_git):
            with patch.object(
                skill, "_stream_to_console", new_callable=AsyncMock, return_value="ok"
            ):
                await skill.execute("", ctx)
                skill._stream_to_console.assert_called_once()

    @patch("deep_coder.skills.pr.print_error")
    async def test_pr_not_on_branch(self, mock_error, ctx):
        skill = PRSkill()
        with patch.object(skill, "_run_git", new_callable=AsyncMock, return_value=(0, "", "")):
            await skill.execute("", ctx)
            mock_error.assert_called_once()

    @patch("deep_coder.skills.pr.print_warning")
    async def test_pr_on_main(self, mock_warning, ctx):
        skill = PRSkill()
        with patch.object(skill, "_run_git", new_callable=AsyncMock, return_value=(0, "main", "")):
            await skill.execute("", ctx)
            mock_warning.assert_called_once()

    @patch("deep_coder.skills.pr.print_warning")
    async def test_pr_no_commits(self, mock_warning, ctx):
        skill = PRSkill()
        call_count = 0

        async def mock_run_git(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (0, "feature", "")
            return (0, "", "")

        with patch.object(skill, "_run_git", side_effect=mock_run_git):
            await skill.execute("", ctx)
            mock_warning.assert_called_once()


class TestCommitSkillExecute:
    @patch("deep_coder.skills.commit.print_warning")
    async def test_commit_no_staged(self, mock_warning, ctx):
        skill = CommitSkill()
        with patch.object(skill, "_run_git", new_callable=AsyncMock, return_value=(0, "", "")):
            await skill.execute("", ctx)
            mock_warning.assert_called_once()

    @patch("deep_coder.skills.commit.print_error")
    async def test_commit_empty_message(self, mock_error, ctx):
        skill = CommitSkill()
        with patch.object(
            skill,
            "_run_git",
            new_callable=AsyncMock,
            return_value=(0, "diff content", ""),
        ):
            ctx.client.collect_stream = AsyncMock(return_value={"content": ""})
            ctx.status_panel = None
            await skill.execute("", ctx)
            mock_error.assert_called_once()

    async def test_commit_message_cleanup(self, ctx):
        skill = CommitSkill()

        async def mock_run_git(*args, **kwargs):
            if "--stat" in args:
                return (0, "file.py | 1 +", "")
            if "commit" in args:
                return (0, "committed", "")
            return (0, "diff content", "")

        with patch.object(skill, "_run_git", side_effect=mock_run_git):
            ctx.client.collect_stream = AsyncMock(
                return_value={"content": "```\nfeat: add feature\n\nDoes stuff\n```"}
            )
            with patch("builtins.input", return_value="y"):
                with patch("deep_coder.skills.commit.print_success") as mock_success:
                    await skill.execute("add feature", ctx)
                    mock_success.assert_called_once()

    async def test_commit_rejected(self, ctx):
        skill = CommitSkill()

        async def mock_run_git(*args, **kwargs):
            if "--stat" in args:
                return (0, "file.py | 1 +", "")
            return (0, "diff content", "")

        with patch.object(skill, "_run_git", side_effect=mock_run_git):
            ctx.client.collect_stream = AsyncMock(return_value={"content": "feat: do stuff"})
            with patch("builtins.input", return_value="n"):
                with patch("deep_coder.skills.commit.print_info") as mock_info:
                    await skill.execute("", ctx)
                    mock_info.assert_called()


class TestTestSkillDetect:
    def test_detect_pytest(self, cwd):
        open(os.path.join(cwd, "pyproject.toml"), "w").close()
        skill = TestSkill()
        assert skill._detect_test_command(cwd) == "python -m pytest -v"

    def test_detect_npm(self, cwd):
        open(os.path.join(cwd, "package.json"), "w").close()
        skill = TestSkill()
        assert skill._detect_test_command(cwd) == "npm test"

    def test_detect_go(self, cwd):
        open(os.path.join(cwd, "go.mod"), "w").close()
        skill = TestSkill()
        assert skill._detect_test_command(cwd) == "go test ./..."

    def test_detect_cargo(self, cwd):
        open(os.path.join(cwd, "Cargo.toml"), "w").close()
        skill = TestSkill()
        assert skill._detect_test_command(cwd) == "cargo test"

    def test_detect_make(self, cwd):
        open(os.path.join(cwd, "Makefile"), "w").close()
        skill = TestSkill()
        assert skill._detect_test_command(cwd) == "make test"

    def test_detect_nothing(self, cwd):
        skill = TestSkill()
        assert skill._detect_test_command(cwd) is None


class TestTestSkillExecute:
    @patch("deep_coder.skills.test_skill.print_error")
    async def test_no_framework_detected(self, mock_error, ctx, cwd):
        skill = TestSkill()
        await skill.execute("", ctx)
        mock_error.assert_called_once()

    @patch("deep_coder.skills.test_skill.print_success")
    async def test_tests_pass(self, mock_success, ctx):
        skill = TestSkill()
        with patch.object(
            skill,
            "_run_shell",
            new_callable=AsyncMock,
            return_value=(0, "4 passed", ""),
        ):
            await skill.execute("echo test", ctx)
            mock_success.assert_called_once()

    async def test_tests_fail_with_analysis(self, ctx):
        skill = TestSkill()
        with patch.object(
            skill,
            "_run_shell",
            new_callable=AsyncMock,
            return_value=(1, "FAILED test_foo", ""),
        ):
            with patch.object(
                skill, "_stream_to_console", new_callable=AsyncMock, return_value="analysis"
            ):
                await skill.execute("echo test", ctx)
                skill._stream_to_console.assert_called_once()
                prompt = skill._stream_to_console.call_args[0][1]
                assert "Test Failure" in prompt
