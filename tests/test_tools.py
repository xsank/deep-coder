"""Tests for the tool system."""

from __future__ import annotations

import os
import tempfile

import pytest

from deep_coder.tools.base import ToolRegistry, create_default_registry
from deep_coder.tools.file_ops import EditFileTool, ReadFileTool, WriteFileTool
from deep_coder.tools.search import GrepFilesTool
from deep_coder.tools.shell import ExecShellTool


@pytest.fixture
def registry():
    return create_default_registry()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestToolRegistry:
    def test_create_default_registry(self, registry: ToolRegistry):
        tools = registry.list_tools()
        names = {t.name for t in tools}
        assert "read_file" in names
        assert "write_file" in names
        assert "edit_file" in names
        assert "list_files" in names
        assert "grep_files" in names
        assert "glob_files" in names
        assert "exec_shell" in names

    def test_openai_tool_schemas(self, registry: ToolRegistry):
        schemas = registry.to_openai_tools()
        assert len(schemas) >= 7
        for schema in schemas:
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self, registry: ToolRegistry):
        result = await registry.dispatch("nonexistent", "{}")
        assert not result.success
        assert "not found" in result.content.lower()

    @pytest.mark.asyncio
    async def test_dispatch_invalid_json(self, registry: ToolRegistry):
        result = await registry.dispatch("read_file", "not json")
        assert not result.success


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("line1\nline2\nline3\n")
        tool = ReadFileTool()
        result = await tool.execute(file_path=path)
        assert result.success
        assert "line1" in result.content
        assert "line2" in result.content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        tool = ReadFileTool()
        result = await tool.execute(file_path="/nonexistent/file.txt")
        assert not result.success

    @pytest.mark.asyncio
    async def test_read_with_offset(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("line1\nline2\nline3\n")
        tool = ReadFileTool()
        result = await tool.execute(file_path=path, offset=1, limit=1)
        assert result.success
        assert "line2" in result.content
        assert "line1" not in result.content


class TestWriteFile:
    @pytest.mark.asyncio
    async def test_write_new_file(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "new.txt")
        tool = WriteFileTool()
        result = await tool.execute(file_path=path, content="hello world")
        assert result.success
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "sub", "dir", "file.txt")
        tool = WriteFileTool()
        result = await tool.execute(file_path=path, content="nested")
        assert result.success
        assert os.path.exists(path)


class TestEditFile:
    @pytest.mark.asyncio
    async def test_edit_single_occurrence(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "edit.txt")
        with open(path, "w") as f:
            f.write("hello world")
        tool = EditFileTool()
        result = await tool.execute(file_path=path, old_string="hello", new_string="goodbye")
        assert result.success
        with open(path) as f:
            assert f.read() == "goodbye world"

    @pytest.mark.asyncio
    async def test_edit_not_found(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "edit.txt")
        with open(path, "w") as f:
            f.write("hello world")
        tool = EditFileTool()
        result = await tool.execute(file_path=path, old_string="xyz", new_string="abc")
        assert not result.success

    @pytest.mark.asyncio
    async def test_edit_ambiguous_without_replace_all(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "edit.txt")
        with open(path, "w") as f:
            f.write("aa bb aa")
        tool = EditFileTool()
        result = await tool.execute(file_path=path, old_string="aa", new_string="cc")
        assert not result.success
        assert "2 times" in result.content


class TestGrepFiles:
    @pytest.mark.asyncio
    async def test_grep_basic(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "code.py")
        with open(path, "w") as f:
            f.write("def hello():\n    return 42\n")
        tool = GrepFilesTool()
        result = await tool.execute(pattern="def hello", path=tmp_dir)
        assert result.success
        assert "hello" in result.content

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, tmp_dir: str):
        path = os.path.join(tmp_dir, "code.py")
        with open(path, "w") as f:
            f.write("def hello():\n    return 42\n")
        tool = GrepFilesTool()
        result = await tool.execute(pattern="nonexistent_function", path=tmp_dir)
        assert result.success
        assert "No matches" in result.content


class TestExecShell:
    @pytest.mark.asyncio
    async def test_echo(self):
        tool = ExecShellTool()
        result = await tool.execute(command="echo hello")
        assert result.success
        assert "hello" in result.content

    @pytest.mark.asyncio
    async def test_failing_command(self):
        tool = ExecShellTool()
        result = await tool.execute(command="false")
        assert not result.success

    @pytest.mark.asyncio
    async def test_timeout(self):
        tool = ExecShellTool()
        result = await tool.execute(command="sleep 10", timeout=1)
        assert not result.success
        assert "timed out" in result.content.lower()
