"""Extended tests for tools/file_ops.py — delete, move, multi-edit, insert, list."""

from __future__ import annotations

import os
import tempfile

import pytest

from deep_coder.tools.file_ops import (
    DeleteFileTool,
    EditFileTool,
    InsertTextTool,
    ListFilesTool,
    MoveFileTool,
    MultiEditFileTool,
    ReadFileTool,
    WriteFileTool,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestReadFileExtended:
    async def test_read_directory(self, tmp_dir):
        tool = ReadFileTool()
        result = await tool.execute(file_path=tmp_dir)
        assert not result.success
        assert "not a file" in result.content.lower()

    async def test_read_more_lines_indicator(self, tmp_dir):
        path = os.path.join(tmp_dir, "big.txt")
        with open(path, "w") as f:
            for i in range(100):
                f.write(f"line {i}\n")
        tool = ReadFileTool()
        result = await tool.execute(file_path=path, limit=10)
        assert result.success
        assert "more lines" in result.content

    async def test_read_only_property(self):
        tool = ReadFileTool()
        assert tool.is_read_only is True
        assert tool.requires_approval is False


class TestWriteFileExtended:
    async def test_write_counts_lines(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        tool = WriteFileTool()
        result = await tool.execute(file_path=path, content="a\nb\nc\n")
        assert result.success
        assert "3 lines" in result.content

    async def test_write_single_line_no_newline(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        tool = WriteFileTool()
        result = await tool.execute(file_path=path, content="hello")
        assert result.success
        assert "1 line" in result.content


class TestEditFileExtended:
    async def test_replace_all(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("aa bb aa cc aa")
        tool = EditFileTool()
        result = await tool.execute(
            file_path=path, old_string="aa", new_string="xx", replace_all=True
        )
        assert result.success
        assert "3 occurrence" in result.content
        with open(path) as f:
            assert f.read() == "xx bb xx cc xx"

    async def test_edit_nonexistent(self, tmp_dir):
        tool = EditFileTool()
        result = await tool.execute(
            file_path=os.path.join(tmp_dir, "nope.txt"),
            old_string="a",
            new_string="b",
        )
        assert not result.success
        assert "not found" in result.content.lower()


class TestDeleteFile:
    async def test_delete_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "to_delete.txt")
        with open(path, "w") as f:
            f.write("content")
        tool = DeleteFileTool()
        result = await tool.execute(file_path=path)
        assert result.success
        assert not os.path.exists(path)

    async def test_delete_empty_dir(self, tmp_dir):
        dir_path = os.path.join(tmp_dir, "empty_dir")
        os.makedirs(dir_path)
        tool = DeleteFileTool()
        result = await tool.execute(file_path=dir_path)
        assert result.success
        assert not os.path.exists(dir_path)

    async def test_delete_nonexistent(self, tmp_dir):
        tool = DeleteFileTool()
        result = await tool.execute(file_path=os.path.join(tmp_dir, "nope.txt"))
        assert not result.success
        assert "not found" in result.content.lower()

    async def test_delete_nonempty_dir(self, tmp_dir):
        dir_path = os.path.join(tmp_dir, "nonempty")
        os.makedirs(dir_path)
        with open(os.path.join(dir_path, "file.txt"), "w") as f:
            f.write("x")
        tool = DeleteFileTool()
        result = await tool.execute(file_path=dir_path)
        assert not result.success


class TestMoveFile:
    async def test_move_file(self, tmp_dir):
        src = os.path.join(tmp_dir, "src.txt")
        dst = os.path.join(tmp_dir, "dst.txt")
        with open(src, "w") as f:
            f.write("content")
        tool = MoveFileTool()
        result = await tool.execute(source=src, destination=dst)
        assert result.success
        assert not os.path.exists(src)
        assert os.path.exists(dst)

    async def test_move_creates_parent(self, tmp_dir):
        src = os.path.join(tmp_dir, "src.txt")
        dst = os.path.join(tmp_dir, "sub", "dir", "dst.txt")
        with open(src, "w") as f:
            f.write("content")
        tool = MoveFileTool()
        result = await tool.execute(source=src, destination=dst)
        assert result.success
        assert os.path.exists(dst)

    async def test_move_nonexistent(self, tmp_dir):
        tool = MoveFileTool()
        result = await tool.execute(
            source=os.path.join(tmp_dir, "nope.txt"),
            destination=os.path.join(tmp_dir, "dst.txt"),
        )
        assert not result.success
        assert "not found" in result.content.lower()


class TestMultiEditFile:
    async def test_multi_edit(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("hello world foo bar")
        tool = MultiEditFileTool()
        result = await tool.execute(
            file_path=path,
            edits=[
                {"old_string": "hello", "new_string": "hi"},
                {"old_string": "foo", "new_string": "baz"},
            ],
        )
        assert result.success
        assert "2 edit" in result.content
        with open(path) as f:
            assert f.read() == "hi world baz bar"

    async def test_multi_edit_missing(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("hello world")
        tool = MultiEditFileTool()
        result = await tool.execute(
            file_path=path,
            edits=[
                {"old_string": "hello", "new_string": "hi"},
                {"old_string": "xyz", "new_string": "abc"},
            ],
        )
        assert not result.success
        assert "#2" in result.content
        with open(path) as f:
            assert f.read() == "hello world"

    async def test_multi_edit_ambiguous(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("aa bb aa")
        tool = MultiEditFileTool()
        result = await tool.execute(
            file_path=path,
            edits=[{"old_string": "aa", "new_string": "cc"}],
        )
        assert not result.success
        assert "2 times" in result.content

    async def test_multi_edit_nonexistent(self, tmp_dir):
        tool = MultiEditFileTool()
        result = await tool.execute(
            file_path=os.path.join(tmp_dir, "nope.txt"),
            edits=[{"old_string": "a", "new_string": "b"}],
        )
        assert not result.success


class TestInsertText:
    async def test_insert_at_beginning(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("line1\nline2\n")
        tool = InsertTextTool()
        result = await tool.execute(file_path=path, line=1, content="new\n")
        assert result.success
        with open(path) as f:
            content = f.read()
        assert content.startswith("new\n")

    async def test_insert_at_end(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("line1\nline2\n")
        tool = InsertTextTool()
        result = await tool.execute(file_path=path, line=999, content="appended")
        assert result.success
        with open(path) as f:
            content = f.read()
        assert "appended" in content

    async def test_insert_nonexistent(self, tmp_dir):
        tool = InsertTextTool()
        result = await tool.execute(
            file_path=os.path.join(tmp_dir, "nope.txt"),
            line=1,
            content="text",
        )
        assert not result.success


class TestListFilesExtended:
    async def test_list_with_pattern(self, tmp_dir):
        for name in ["a.py", "b.py", "c.txt"]:
            with open(os.path.join(tmp_dir, name), "w") as f:
                f.write("x")
        tool = ListFilesTool()
        result = await tool.execute(path=tmp_dir, pattern="*.py")
        assert result.success
        assert "a.py" in result.content
        assert "b.py" in result.content
        assert "c.txt" not in result.content

    async def test_list_empty_dir(self, tmp_dir):
        empty = os.path.join(tmp_dir, "empty")
        os.makedirs(empty)
        tool = ListFilesTool()
        result = await tool.execute(path=empty)
        assert result.success
        assert "empty" in result.content.lower()

    async def test_list_nonexistent(self, tmp_dir):
        tool = ListFilesTool()
        result = await tool.execute(path=os.path.join(tmp_dir, "nope"))
        assert not result.success

    async def test_list_file_not_dir(self, tmp_dir):
        path = os.path.join(tmp_dir, "file.txt")
        with open(path, "w") as f:
            f.write("x")
        tool = ListFilesTool()
        result = await tool.execute(path=path)
        assert not result.success
        assert "not a directory" in result.content.lower()

    async def test_list_shows_dirs(self, tmp_dir):
        os.makedirs(os.path.join(tmp_dir, "subdir"))
        with open(os.path.join(tmp_dir, "file.txt"), "w") as f:
            f.write("x")
        tool = ListFilesTool()
        result = await tool.execute(path=tmp_dir)
        assert result.success
        assert "d subdir" in result.content
        assert "f file.txt" in result.content
