"""Tests for the display module."""

from __future__ import annotations

from deep_coder.display import (
    StreamPrinter,
    _format_elapsed,
    summarize_tool_args,
    summarize_tool_result,
)


class TestFormatElapsed:
    def test_seconds(self):
        assert _format_elapsed(5.2) == "5s"
        assert _format_elapsed(0.3) == "0s"
        assert _format_elapsed(59.9) == "60s"

    def test_minutes(self):
        assert _format_elapsed(60) == "1m 0s"
        assert _format_elapsed(90) == "1m 30s"
        assert _format_elapsed(125) == "2m 5s"


class TestHasOpenFence:
    def test_no_fence(self):
        assert StreamPrinter._has_open_fence("hello world\n") is False

    def test_closed_fence(self):
        text = "```python\nprint('hi')\n```\n"
        assert StreamPrinter._has_open_fence(text) is False

    def test_open_fence(self):
        text = "```python\nprint('hi')\n"
        assert StreamPrinter._has_open_fence(text) is True

    def test_tilde_fence(self):
        text = "~~~\ncode\n"
        assert StreamPrinter._has_open_fence(text) is True

    def test_tilde_closed(self):
        text = "~~~\ncode\n~~~\n"
        assert StreamPrinter._has_open_fence(text) is False

    def test_nested_backticks_in_fence(self):
        text = "````\n```\ninner\n```\n"
        assert StreamPrinter._has_open_fence(text) is True

    def test_four_backtick_closed(self):
        text = "````\nsome code\n````\n"
        assert StreamPrinter._has_open_fence(text) is False

    def test_indented_more_than_3_ignored(self):
        text = "    ```\nindented code block\n"
        assert StreamPrinter._has_open_fence(text) is False

    def test_indent_3_spaces(self):
        text = "   ```\ncode\n"
        assert StreamPrinter._has_open_fence(text) is True

    def test_multiple_fences(self):
        text = "```\nfirst\n```\n```\nsecond\n"
        assert StreamPrinter._has_open_fence(text) is True

    def test_multiple_fences_all_closed(self):
        text = "```\nfirst\n```\n```\nsecond\n```\n"
        assert StreamPrinter._has_open_fence(text) is False

    def test_fence_with_info_string(self):
        text = "```javascript\nconsole.log('hi');\n"
        assert StreamPrinter._has_open_fence(text) is True


class TestFindSafeSplit:
    def _split(self, text: str) -> int:
        printer = StreamPrinter.__new__(StreamPrinter)
        return printer._find_safe_split(text)

    def test_no_fence_returns_zero(self):
        text = "line1\nline2\nline3\n"
        assert self._split(text) == 0

    def test_open_fence_returns_before_fence(self):
        text = "before\n```python\ncode inside\n"
        pos = self._split(text)
        assert pos == len("before\n")

    def test_closed_fence_returns_zero(self):
        text = "before\n```\ncode\n```\nafter\n"
        pos = self._split(text)
        assert pos == 0

    def test_only_fence(self):
        text = "```\ncode\n"
        pos = self._split(text)
        assert pos == 0


class TestSummarizeToolArgs:
    def test_read_file(self):
        result = summarize_tool_args("read_file", '{"file_path": "/src/main.py"}')
        assert result == "main.py"

    def test_exec_shell(self):
        result = summarize_tool_args("exec_shell", '{"command": "ls -la"}')
        assert result == "ls -la"

    def test_exec_shell_long(self):
        cmd = "x" * 60
        result = summarize_tool_args("exec_shell", f'{{"command": "{cmd}"}}')
        assert len(result) <= 53
        assert result.endswith("...")

    def test_grep_files(self):
        result = summarize_tool_args("grep_files", '{"pattern": "TODO", "glob": "*.py"}')
        assert '"TODO"' in result
        assert "*.py" in result

    def test_glob_files(self):
        result = summarize_tool_args("glob_files", '{"pattern": "**/*.ts"}')
        assert result == "**/*.ts"

    def test_list_files(self):
        result = summarize_tool_args("list_files", '{"path": "/src"}')
        assert result == "/src"

    def test_git_commit(self):
        result = summarize_tool_args("git_commit", '{"message": "fix: typo"}')
        assert result == "fix: typo"

    def test_invalid_json(self):
        result = summarize_tool_args("read_file", "not json")
        assert result == ""

    def test_unknown_tool(self):
        result = summarize_tool_args("custom_tool", '{"a": 1}')
        assert result == ""

    def test_write_file(self):
        result = summarize_tool_args("write_file", '{"file_path": "/src/utils.py"}')
        assert result == "utils.py"

    def test_move_file(self):
        result = summarize_tool_args(
            "move_file",
            '{"source": "/old/a.py", "destination": "/new/b.py"}',
        )
        assert "a.py" in result
        assert "b.py" in result


class TestSummarizeToolResult:
    def test_read_file(self):
        content = "line1\nline2\nline3\n"
        result = summarize_tool_result("read_file", content, True)
        assert "3 lines" in result

    def test_read_file_single_line(self):
        result = summarize_tool_result("read_file", "single", True)
        assert result == "ok"

    def test_grep_matches(self):
        result = summarize_tool_result("grep_files", "match1\nmatch2\n", True)
        assert "2 matches" in result

    def test_grep_no_matches(self):
        result = summarize_tool_result("grep_files", "", True)
        assert "0 matches" in result

    def test_glob_files(self):
        result = summarize_tool_result("glob_files", "a.py\nb.py\n", True)
        assert "2 files" in result

    def test_exec_shell_ok(self):
        result = summarize_tool_result("exec_shell", "output", True)
        assert result == "ok"

    def test_exec_shell_error(self):
        result = summarize_tool_result("exec_shell", "exit code: 1", True)
        assert result == "error"

    def test_failed(self):
        result = summarize_tool_result("any_tool", "error msg", False)
        assert result == "failed"

    def test_web_search(self):
        result = summarize_tool_result("web_search", "r1\n\nr2\n\nr3", True)
        assert "2 results" in result

    def test_web_fetch(self):
        result = summarize_tool_result("web_fetch", "x" * 100, True)
        assert "100 chars" in result

    def test_unknown_tool(self):
        result = summarize_tool_result("custom", "data", True)
        assert result == "ok"
