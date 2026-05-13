"""Extended tests for tools/base.py — ToolResult, SnapshotTracker, ToolRegistry."""

from __future__ import annotations

import os
import tempfile

import pytest

from deep_coder.tools.base import (
    SnapshotTracker,
    Tool,
    ToolRegistry,
    ToolResult,
)


class TestToolResult:
    def test_ok(self):
        r = ToolResult.ok("success")
        assert r.success is True
        assert r.content == "success"
        assert r.metadata is None

    def test_ok_with_metadata(self):
        r = ToolResult.ok("done", key="value")
        assert r.metadata == {"key": "value"}

    def test_error(self):
        r = ToolResult.error("failed")
        assert r.success is False
        assert r.content == "failed"


class DummyTool(Tool):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "A dummy tool"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.ok("dummy result")


class ReadOnlyTool(Tool):
    @property
    def name(self) -> str:
        return "reader"

    @property
    def description(self) -> str:
        return "Read-only tool"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    @property
    def is_read_only(self) -> bool:
        return True

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.ok("read result")


class TestToolBase:
    def test_default_read_only(self):
        tool = DummyTool()
        assert tool.is_read_only is False

    def test_default_requires_approval(self):
        tool = DummyTool()
        assert tool.requires_approval is True

    def test_read_only_no_approval(self):
        tool = ReadOnlyTool()
        assert tool.is_read_only is True
        assert tool.requires_approval is False

    def test_openai_schema(self):
        tool = DummyTool()
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "dummy"
        assert schema["function"]["description"] == "A dummy tool"
        assert "parameters" in schema["function"]


class TestSnapshotTracker:
    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_capture_existing_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("original")

        tracker = SnapshotTracker()
        tracker.capture(path)
        assert len(tracker._snapshots) == 1
        assert tracker._snapshots[0].existed is True
        assert tracker._snapshots[0].original_content == "original"

    def test_capture_nonexistent_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "nonexistent.txt")
        tracker = SnapshotTracker()
        tracker.capture(path)
        assert len(tracker._snapshots) == 1
        assert tracker._snapshots[0].existed is False
        assert tracker._snapshots[0].original_content is None

    def test_capture_idempotent(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("content")

        tracker = SnapshotTracker()
        tracker.capture(path)
        tracker.capture(path)
        assert len(tracker._snapshots) == 1

    def test_undo_restores_content(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("original")

        tracker = SnapshotTracker()
        tracker.capture(path)

        with open(path, "w") as f:
            f.write("modified")

        undone = tracker.undo_last()
        assert undone is not None
        with open(path) as f:
            assert f.read() == "original"

    def test_undo_removes_new_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "new.txt")
        tracker = SnapshotTracker()
        tracker.capture(path)

        with open(path, "w") as f:
            f.write("new content")

        tracker.undo_last()
        assert not os.path.exists(path)

    def test_undo_empty(self):
        tracker = SnapshotTracker()
        assert tracker.undo_last() is None

    def test_get_diffs(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("original")

        tracker = SnapshotTracker()
        tracker.capture(path)

        with open(path, "w") as f:
            f.write("modified")

        diffs = tracker.get_diffs()
        assert len(diffs) == 1
        assert diffs[0][1] == "original"
        assert diffs[0][2] == "modified"

    def test_get_diffs_no_change(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("same")

        tracker = SnapshotTracker()
        tracker.capture(path)

        diffs = tracker.get_diffs()
        assert len(diffs) == 0

    def test_has_changes(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("original")

        tracker = SnapshotTracker()
        tracker.capture(path)
        assert not tracker.has_changes

        with open(path, "w") as f:
            f.write("modified")
        assert tracker.has_changes

    def test_clear(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("content")

        tracker = SnapshotTracker()
        tracker.capture(path)
        tracker.clear()
        assert len(tracker._snapshots) == 0
        assert len(tracker._modified_files) == 0


class TestToolRegistryExtended:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert registry.get("dummy") is tool

    def test_get_nonexistent(self):
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        registry.register(ReadOnlyTool())
        tools = registry.list_tools()
        names = {t.name for t in tools}
        assert names == {"dummy", "reader"}

    def test_to_openai_tools(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        schemas = registry.to_openai_tools()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "dummy"

    async def test_dispatch_success(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        result = await registry.dispatch("dummy", "{}")
        assert result.success
        assert result.content == "dummy result"

    async def test_dispatch_not_found(self):
        registry = ToolRegistry()
        result = await registry.dispatch("missing", "{}")
        assert not result.success
        assert "not found" in result.content.lower()

    async def test_dispatch_invalid_json(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        result = await registry.dispatch("dummy", "not json")
        assert not result.success
        assert "json" in result.content.lower()

    async def test_dispatch_type_error(self):
        registry = ToolRegistry()

        class BadTool(Tool):
            @property
            def name(self):
                return "bad"

            @property
            def description(self):
                return "Bad"

            @property
            def parameters(self):
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs):
                raise TypeError("wrong args")

        registry.register(BadTool())
        result = await registry.dispatch("bad", "{}")
        assert not result.success
        assert "invalid arguments" in result.content.lower()
