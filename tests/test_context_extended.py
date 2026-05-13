"""Extended tests for context.py — directory tree, truncation, project context."""

from __future__ import annotations

import os
import tempfile

from deep_coder.context import (
    ProjectContext,
    _build_directory_tree,
    _truncate_lines,
    collect_project_context,
)


class TestBuildDirectoryTree:
    def test_basic_tree(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "file.py"), "w") as f:
                f.write("x")
            os.makedirs(os.path.join(d, "subdir"))
            with open(os.path.join(d, "subdir", "inner.py"), "w") as f:
                f.write("x")
            tree = _build_directory_tree(d)
            assert "file.py" in tree
            assert "subdir/" in tree
            assert "inner.py" in tree

    def test_skips_hidden_files(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".hidden"), "w") as f:
                f.write("x")
            with open(os.path.join(d, "visible.py"), "w") as f:
                f.write("x")
            tree = _build_directory_tree(d)
            assert ".hidden" not in tree
            assert "visible.py" in tree

    def test_skips_special_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "__pycache__"))
            os.makedirs(os.path.join(d, "node_modules"))
            os.makedirs(os.path.join(d, "src"))
            tree = _build_directory_tree(d)
            assert "__pycache__" not in tree
            assert "node_modules" not in tree
            assert "src/" in tree

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            tree = _build_directory_tree(d)
            assert tree == ""

    def test_depth_limit(self):
        with tempfile.TemporaryDirectory() as d:
            deep = os.path.join(d, "a", "b", "c", "d", "e")
            os.makedirs(deep)
            with open(os.path.join(deep, "deep.py"), "w") as f:
                f.write("x")
            tree = _build_directory_tree(d, max_depth=2)
            assert "a/" in tree
            assert "deep.py" not in tree


class TestTruncateLines:
    def test_short_text(self):
        text = "line1\nline2\nline3"
        assert _truncate_lines(text, 5) == text

    def test_exactly_at_limit(self):
        text = "a\nb\nc"
        assert _truncate_lines(text, 3) == text

    def test_truncated(self):
        text = "a\nb\nc\nd\ne"
        result = _truncate_lines(text, 2)
        assert "a\nb" in result
        assert "3 more" in result


class TestCollectProjectContext:
    async def test_none_cwd(self):
        result = await collect_project_context(None)
        assert result is None

    async def test_git_repo(self):
        with tempfile.TemporaryDirectory() as d:
            os.system(
                f"cd {d} && git init -q"
                f" && git config user.email 'test@test.com'"
                f" && git config user.name 'Test'"
            )
            with open(os.path.join(d, "file.py"), "w") as f:
                f.write("x")
            os.system(f"cd {d} && git add . && git commit -q -m 'init'")
            result = await collect_project_context(d)
            assert result is not None
            assert result.is_git_repo is True
            assert result.git_branch != ""

    async def test_non_git_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "file.py"), "w") as f:
                f.write("x")
            result = await collect_project_context(d)
            assert result is not None
            assert result.is_git_repo is False

    async def test_format_for_prompt_git(self):
        ctx = ProjectContext(
            git_branch="main",
            git_status="M file.py",
            git_recent_commits="abc123 init",
            directory_tree="file.py\nsubdir/",
            is_git_repo=True,
        )
        text = ctx.format_for_prompt()
        assert "Branch: main" in text
        assert "M file.py" in text
        assert "abc123" in text
        assert "file.py" in text

    async def test_format_for_prompt_clean(self):
        ctx = ProjectContext(
            git_branch="main",
            git_status="",
            git_recent_commits="",
            directory_tree="",
            is_git_repo=True,
        )
        text = ctx.format_for_prompt()
        assert "(clean)" in text
