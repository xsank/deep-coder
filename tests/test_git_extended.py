"""Extended tests for tools/git.py — git tool properties and execution."""

from __future__ import annotations

import os
import tempfile

import pytest

from deep_coder.tools.git import (
    GitBranchTool,
    GitCheckoutTool,
    GitCommitTool,
    GitDiffTool,
    GitLogTool,
    GitStatusTool,
)


@pytest.fixture
def git_repo():
    """Create a temporary git repository."""
    with tempfile.TemporaryDirectory() as d:
        os.system(
            f"cd {d} && git init -q"
            f" && git config user.email 'test@test.com'"
            f" && git config user.name 'Test'"
        )
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write("# Test\n")
        os.system(f"cd {d} && git add . && git commit -q -m 'init'")
        yield d


class TestGitToolProperties:
    def test_status_read_only(self):
        tool = GitStatusTool()
        assert tool.name == "git_status"
        assert tool.is_read_only is True

    def test_diff_read_only(self):
        tool = GitDiffTool()
        assert tool.name == "git_diff"
        assert tool.is_read_only is True

    def test_log_read_only(self):
        tool = GitLogTool()
        assert tool.name == "git_log"
        assert tool.is_read_only is True

    def test_branch_requires_approval(self):
        tool = GitBranchTool()
        assert tool.name == "git_branch"
        assert tool.requires_approval is True

    def test_checkout_requires_approval(self):
        tool = GitCheckoutTool()
        assert tool.name == "git_checkout"
        assert tool.requires_approval is True

    def test_commit_name(self):
        tool = GitCommitTool()
        assert tool.name == "git_commit"

    def test_all_have_parameters(self):
        for cls in [
            GitStatusTool,
            GitDiffTool,
            GitLogTool,
            GitBranchTool,
            GitCheckoutTool,
            GitCommitTool,
        ]:
            tool = cls()
            assert "type" in tool.parameters

    def test_all_have_schemas(self):
        for cls in [
            GitStatusTool,
            GitDiffTool,
            GitLogTool,
            GitBranchTool,
            GitCheckoutTool,
            GitCommitTool,
        ]:
            schema = cls().to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]


class TestGitStatusTool:
    async def test_clean_repo(self, git_repo):
        tool = GitStatusTool()
        result = await tool.execute()
        assert result.success

    async def test_with_changes(self, git_repo):
        with open(os.path.join(git_repo, "new.txt"), "w") as f:
            f.write("new file")
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitStatusTool()
            result = await tool.execute()
            assert result.success
            assert "new.txt" in result.content
        finally:
            os.chdir(old_cwd)


class TestGitDiffTool:
    async def test_no_diff(self, git_repo):
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitDiffTool()
            result = await tool.execute()
            assert result.success
            assert "no differences" in result.content.lower()
        finally:
            os.chdir(old_cwd)

    async def test_staged_diff(self, git_repo):
        path = os.path.join(git_repo, "README.md")
        with open(path, "w") as f:
            f.write("# Updated\n")
        os.system(f"cd {git_repo} && git add README.md")
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitDiffTool()
            result = await tool.execute(staged=True)
            assert result.success
            assert "Updated" in result.content or "README" in result.content
        finally:
            os.chdir(old_cwd)


class TestGitLogTool:
    async def test_log(self, git_repo):
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitLogTool()
            result = await tool.execute(count=5)
            assert result.success
            assert "init" in result.content
        finally:
            os.chdir(old_cwd)

    async def test_log_oneline_false(self, git_repo):
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitLogTool()
            result = await tool.execute(count=5, oneline=False)
            assert result.success
        finally:
            os.chdir(old_cwd)


class TestGitCommitTool:
    async def test_commit_no_files_no_all(self, git_repo):
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitCommitTool()
            result = await tool.execute(message="test")
            assert not result.success
            assert "specify" in result.content.lower()
        finally:
            os.chdir(old_cwd)

    async def test_commit_with_all(self, git_repo):
        path = os.path.join(git_repo, "new.txt")
        with open(path, "w") as f:
            f.write("new")
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitCommitTool()
            result = await tool.execute(message="add new file", all=True)
            assert result.success
        finally:
            os.chdir(old_cwd)

    async def test_commit_with_files(self, git_repo):
        path = os.path.join(git_repo, "another.txt")
        with open(path, "w") as f:
            f.write("another")
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitCommitTool()
            result = await tool.execute(message="add another", files=["another.txt"])
            assert result.success
        finally:
            os.chdir(old_cwd)


class TestGitBranchTool:
    async def test_list_branches(self, git_repo):
        old_cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            tool = GitBranchTool()
            result = await tool.execute()
            assert result.success
        finally:
            os.chdir(old_cwd)
