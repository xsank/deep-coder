"""Tests for the project context module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from deep_coder.context import (
    ProjectContext,
    _build_directory_tree,
    _truncate_lines,
)


class TestProjectContext:
    def test_format_git_repo(self):
        ctx = ProjectContext(
            git_branch="main",
            git_status="M file.py",
            git_recent_commits="abc123 Initial commit",
            directory_tree="file.py\nREADME.md",
            is_git_repo=True,
        )
        output = ctx.format_for_prompt()
        assert "Branch: main" in output
        assert "M file.py" in output
        assert "abc123" in output
        assert "file.py" in output

    def test_format_clean_repo(self):
        ctx = ProjectContext(
            git_branch="main",
            git_status="",
            git_recent_commits="",
            directory_tree="",
            is_git_repo=True,
        )
        output = ctx.format_for_prompt()
        assert "Branch: main" in output
        assert "(clean)" in output

    def test_format_non_git(self):
        ctx = ProjectContext(
            git_branch="",
            git_status="",
            git_recent_commits="",
            directory_tree="file.txt",
            is_git_repo=False,
        )
        output = ctx.format_for_prompt()
        assert "Branch" not in output
        assert "file.txt" in output


class TestBuildDirectoryTree:
    def test_basic_tree(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "file_a.py").touch()
            (Path(d) / "file_b.txt").touch()
            tree = _build_directory_tree(d)
            assert "file_a.py" in tree
            assert "file_b.txt" in tree

    def test_nested_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d) / "src"
            sub.mkdir()
            (sub / "main.py").touch()
            tree = _build_directory_tree(d)
            assert "src/" in tree
            assert "main.py" in tree

    def test_skips_hidden_files(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".hidden").touch()
            (Path(d) / "visible.py").touch()
            tree = _build_directory_tree(d)
            assert ".hidden" not in tree
            assert "visible.py" in tree

    def test_skips_excluded_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "__pycache__").mkdir()
            (Path(d) / "__pycache__" / "cached.pyc").touch()
            (Path(d) / "src").mkdir()
            (Path(d) / "src" / "app.py").touch()
            tree = _build_directory_tree(d)
            assert "__pycache__" not in tree
            assert "app.py" in tree

    def test_respects_max_depth(self):
        with tempfile.TemporaryDirectory() as d:
            deep = Path(d) / "a" / "b" / "c" / "d" / "e"
            deep.mkdir(parents=True)
            (deep / "deep_file.py").touch()
            tree = _build_directory_tree(d, max_depth=2)
            assert "a/" in tree
            assert "b/" in tree


class TestTruncateLines:
    def test_short_text(self):
        text = "line1\nline2\nline3"
        assert _truncate_lines(text, 5) == text

    def test_exact_limit(self):
        text = "l1\nl2\nl3"
        assert _truncate_lines(text, 3) == text

    def test_truncation(self):
        text = "\n".join(f"line{i}" for i in range(20))
        result = _truncate_lines(text, 5)
        assert result.count("\n") == 5
        assert "15 more" in result
