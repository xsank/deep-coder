"""Extended tests for tools/search.py — grep and glob tools."""

from __future__ import annotations

import os
import tempfile

import pytest

from deep_coder.tools.search import GlobFilesTool, GrepFilesTool


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestGrepFilesExtended:
    async def test_case_insensitive(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.py")
        with open(path, "w") as f:
            f.write("Hello World\nhello world\n")
        tool = GrepFilesTool()
        result = await tool.execute(
            pattern="hello",
            path=tmp_dir,
            case_insensitive=True,
        )
        assert result.success
        assert result.content.count("test.py") == 2

    async def test_invalid_regex(self, tmp_dir):
        tool = GrepFilesTool()
        result = await tool.execute(pattern="[invalid", path=tmp_dir)
        assert not result.success
        assert "invalid regex" in result.content.lower()

    async def test_path_not_found(self):
        tool = GrepFilesTool()
        result = await tool.execute(pattern="test", path="/nonexistent/path")
        assert not result.success
        assert "not found" in result.content.lower()

    async def test_search_single_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "code.py")
        with open(path, "w") as f:
            f.write("def foo():\n    return 42\n")
        tool = GrepFilesTool()
        result = await tool.execute(pattern="return", path=path)
        assert result.success
        assert "42" in result.content

    async def test_glob_filter(self, tmp_dir):
        for name, content in [("a.py", "target"), ("b.txt", "target")]:
            with open(os.path.join(tmp_dir, name), "w") as f:
                f.write(content)
        tool = GrepFilesTool()
        result = await tool.execute(pattern="target", path=tmp_dir, glob="*.py")
        assert result.success
        assert "a.py" in result.content

    async def test_max_results(self, tmp_dir):
        path = os.path.join(tmp_dir, "many.py")
        with open(path, "w") as f:
            for i in range(50):
                f.write(f"match_{i}\n")
        tool = GrepFilesTool()
        result = await tool.execute(pattern="match_", path=tmp_dir, max_results=5)
        assert result.success
        assert "truncated" in result.content

    async def test_skips_binary_files(self, tmp_dir):
        py_path = os.path.join(tmp_dir, "code.py")
        with open(py_path, "w") as f:
            f.write("target\n")
        bin_path = os.path.join(tmp_dir, "image.png")
        with open(bin_path, "wb") as f:
            f.write(b"target\n")
        tool = GrepFilesTool()
        result = await tool.execute(pattern="target", path=tmp_dir)
        assert result.success
        assert "code.py" in result.content
        assert "image.png" not in result.content

    def test_properties(self):
        tool = GrepFilesTool()
        assert tool.is_read_only is True
        assert tool.requires_approval is False


class TestGlobFilesExtended:
    async def test_basic_glob(self, tmp_dir):
        for name in ["a.py", "b.py", "c.txt"]:
            with open(os.path.join(tmp_dir, name), "w") as f:
                f.write("x")
        tool = GlobFilesTool()
        result = await tool.execute(pattern="*.py", path=tmp_dir)
        assert result.success
        assert "a.py" in result.content
        assert "b.py" in result.content
        assert "c.txt" not in result.content

    async def test_no_matches(self, tmp_dir):
        tool = GlobFilesTool()
        result = await tool.execute(pattern="*.xyz", path=tmp_dir)
        assert result.success
        assert "no matches" in result.content.lower()

    async def test_path_not_found(self):
        tool = GlobFilesTool()
        result = await tool.execute(pattern="*.py", path="/nonexistent")
        assert not result.success

    async def test_max_results(self, tmp_dir):
        for i in range(20):
            with open(os.path.join(tmp_dir, f"file_{i}.py"), "w") as f:
                f.write("x")
        tool = GlobFilesTool()
        result = await tool.execute(pattern="*.py", path=tmp_dir, max_results=5)
        assert result.success
        assert "more files" in result.content

    def test_properties(self):
        tool = GlobFilesTool()
        assert tool.is_read_only is True
        assert tool.requires_approval is False
