"""Extended tests for display.py — more coverage of display functions."""

from __future__ import annotations

from deep_coder.display import (
    _PHASE_STYLES,
    print_file_diff,
    print_phase,
    print_plan_summary,
    print_task_status,
    print_tool_call,
    summarize_tool_args,
    summarize_tool_result,
)


class TestPrintToolCall:
    def test_calling(self, capsys):
        print_tool_call("read_file", "calling")

    def test_completed(self, capsys):
        print_tool_call("write_file", "completed")

    def test_failed(self, capsys):
        print_tool_call("exec_shell", "failed")

    def test_unknown_status(self, capsys):
        print_tool_call("unknown", "other")


class TestPrintPhase:
    def test_known_phases(self, capsys):
        for phase in _PHASE_STYLES:
            print_phase(phase)

    def test_with_detail(self, capsys):
        print_phase("planning", detail="analyzing request")

    def test_unknown_phase(self, capsys):
        print_phase("custom_phase", detail="test")


class TestPrintTaskStatus:
    def test_tool_status(self, capsys):
        print_task_status("t1", "tool:read_file")

    def test_tool_status_no_task(self, capsys):
        print_task_status(None, "tool:read_file")

    def test_plan_status(self, capsys):
        print_task_status(None, "plan:3 tasks")

    def test_running(self, capsys):
        print_task_status("t1", "running")

    def test_running_no_task(self, capsys):
        print_task_status(None, "running")

    def test_completed(self, capsys):
        print_task_status("t1", "completed")

    def test_completed_no_task(self, capsys):
        print_task_status(None, "completed")

    def test_failed(self, capsys):
        print_task_status("t1", "failed:some error")

    def test_failed_no_detail(self, capsys):
        print_task_status("t1", "failed")

    def test_failed_no_task(self, capsys):
        print_task_status(None, "failed:err")


class TestPrintPlanSummary:
    def test_basic(self, capsys):
        tasks = [
            {"id": "t1", "desc": "First task", "deps": []},
            {"id": "t2", "desc": "Second task", "deps": ["t1"]},
        ]
        print_plan_summary("Test plan", tasks)

    def test_single_task(self, capsys):
        tasks = [{"id": "t1", "desc": "Only task", "deps": []}]
        print_plan_summary("Single", tasks)


class TestPrintFileDiff:
    def test_new_file(self, capsys):
        print_file_diff("/tmp/test.py", None, "print('hello')\n")

    def test_delete_file(self, capsys):
        print_file_diff("/tmp/test.py", "old content\n", None)

    def test_no_change(self, capsys):
        print_file_diff("/tmp/test.py", "same\n", "same\n")

    def test_update_file(self, capsys):
        print_file_diff(
            "/tmp/test.py",
            "line1\nline2\nline3\n",
            "line1\nmodified\nline3\n",
        )

    def test_python_file_highlighting(self, capsys):
        print_file_diff(
            "/tmp/test.py",
            "def foo():\n    return 1\n",
            "def foo():\n    return 2\n",
        )

    def test_unknown_extension(self, capsys):
        print_file_diff(
            "/tmp/test.xyz",
            "old\n",
            "new\n",
        )


class TestSummarizeToolArgsExtended:
    def test_edit_file(self):
        result = summarize_tool_args("edit_file", '{"file_path": "/src/app.js"}')
        assert result == "app.js"

    def test_multi_edit_file(self):
        result = summarize_tool_args("multi_edit_file", '{"file_path": "/src/app.js"}')
        assert result == "app.js"

    def test_insert_text(self):
        result = summarize_tool_args("insert_text", '{"file_path": "/src/a.py"}')
        assert result == "a.py"

    def test_delete_file(self):
        result = summarize_tool_args("delete_file", '{"file_path": "/src/old.py"}')
        assert result == "old.py"

    def test_move_file_no_source(self):
        result = summarize_tool_args("move_file", '{"destination": "/new/b.py"}')
        assert result == ""

    def test_grep_no_glob(self):
        result = summarize_tool_args("grep_files", '{"pattern": "TODO"}')
        assert '"TODO"' in result

    def test_git_checkout(self):
        result = summarize_tool_args("git_checkout", '{"branch": "feature"}')
        assert result == "feature"

    def test_web_search(self):
        result = summarize_tool_args("web_search", '{"query": "python docs"}')
        assert result == "python docs"

    def test_web_fetch(self):
        result = summarize_tool_args("web_fetch", '{"url": "https://docs.python.org/3/"}')
        assert "docs.python.org" in result

    def test_empty_args(self):
        result = summarize_tool_args("read_file", "")
        assert result == ""

    def test_none_args(self):
        result = summarize_tool_args("read_file", None)
        assert result == ""

    def test_list_files_default(self):
        result = summarize_tool_args("list_files", "{}")
        assert result == "."


class TestSummarizeToolResultExtended:
    def test_list_files(self):
        result = summarize_tool_result("list_files", "a.py\nb.py\nc.py\n", True)
        assert "3 files" in result

    def test_list_files_empty(self):
        result = summarize_tool_result("list_files", "", True)
        assert "empty" in result

    def test_web_search_no_results(self):
        result = summarize_tool_result("web_search", "", True)
        assert "0 results" in result

    def test_read_file_empty(self):
        result = summarize_tool_result("read_file", "", True)
        assert result == "ok"
