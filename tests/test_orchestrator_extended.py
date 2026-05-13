"""Extended tests for orchestrator.py — plan extraction, verdict parsing, helpers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from deep_coder.agent.orchestrator import Orchestrator, _make_assistant_msg
from deep_coder.agent.task import Plan, Task
from deep_coder.client import DeepSeekClient
from deep_coder.config import AgentConfig, Config, ModelConfig
from deep_coder.tools.base import ToolRegistry


@pytest.fixture
def config():
    return Config(
        model=ModelConfig(api_key="test"),
        agent=AgentConfig(max_workers=2),
    )


@pytest.fixture
def client(config):
    return DeepSeekClient(config)


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture
def orchestrator(client, config, registry):
    orch = Orchestrator(client, config, registry)
    orch.set_cwd("/tmp/test-project")
    return orch


class TestMakeAssistantMsg:
    def test_basic(self):
        resp = {"content": "hello", "role": "assistant"}
        msg = _make_assistant_msg(resp)
        assert msg["role"] == "assistant"
        assert msg["content"] == "hello"
        assert "reasoning_content" not in msg
        assert "tool_calls" not in msg

    def test_with_reasoning(self):
        resp = {"content": "answer", "reasoning_content": "thinking..."}
        msg = _make_assistant_msg(resp)
        assert msg["reasoning_content"] == "thinking..."

    def test_with_tool_calls(self):
        resp = {"content": None, "tool_calls": [{"id": "tc1"}]}
        msg = _make_assistant_msg(resp)
        assert msg["tool_calls"] == [{"id": "tc1"}]

    def test_dsml_stripped(self):
        resp = {"content": "before<DSML>hidden</DSML>after"}
        msg = _make_assistant_msg(resp)
        assert "DSML" not in msg["content"]

    def test_none_content(self):
        resp = {"content": None}
        msg = _make_assistant_msg(resp)
        assert msg["content"] is None


class TestTryExtractPlan:
    def test_json_fenced_plan(self, orchestrator):
        content = (
            'Here is the plan:\n```json\n{"plan": "Test plan",'
            ' "tasks": [{"id": "t1", "description": "Do thing"}]}\n```'
        )
        plan = orchestrator._try_extract_plan(content)
        assert plan is not None
        assert plan.description == "Test plan"
        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == "t1"

    def test_inline_json(self, orchestrator):
        content = 'I will do this: {"tasks": [{"id": "t1", "description": "Read file"}]} end'
        plan = orchestrator._try_extract_plan(content)
        assert plan is not None
        assert len(plan.tasks) == 1

    def test_no_plan(self, orchestrator):
        content = "This is just a regular response with no JSON."
        plan = orchestrator._try_extract_plan(content)
        assert plan is None

    def test_invalid_json(self, orchestrator):
        content = "```json\n{invalid json}\n```"
        plan = orchestrator._try_extract_plan(content)
        assert plan is None

    def test_json_without_tasks(self, orchestrator):
        content = '```json\n{"key": "value"}\n```'
        plan = orchestrator._try_extract_plan(content)
        assert plan is None

    def test_tasks_not_list(self, orchestrator):
        content = '```json\n{"tasks": "not a list"}\n```'
        plan = orchestrator._try_extract_plan(content)
        assert plan is None

    def test_multi_task_with_deps(self, orchestrator):
        plan_data = {
            "plan": "Multi-step",
            "tasks": [
                {"id": "t1", "description": "First"},
                {"id": "t2", "description": "Second", "depends_on": ["t1"]},
            ],
        }
        content = f"```json\n{json.dumps(plan_data)}\n```"
        plan = orchestrator._try_extract_plan(content)
        assert plan is not None
        assert len(plan.tasks) == 2
        assert plan.tasks[1].depends_on == ["t1"]


class TestParseVerdict:
    def test_complete(self, orchestrator):
        content = '```json\n{"status": "complete"}\n```\nAll done. Report here.'
        status, reason, body = orchestrator._parse_verdict(content)
        assert status == "complete"
        assert reason == ""
        assert "All done" in body

    def test_continue_with_reason(self, orchestrator):
        content = '```json\n{"status": "continue", "reason": "Need more work"}\n```\nNew plan...'
        status, reason, body = orchestrator._parse_verdict(content)
        assert status == "continue"
        assert reason == "Need more work"
        assert "New plan" in body

    def test_no_verdict_defaults_complete(self, orchestrator):
        content = "Just a regular response with no verdict JSON."
        status, reason, body = orchestrator._parse_verdict(content)
        assert status == "complete"
        assert reason == ""
        assert body == content

    def test_invalid_json_defaults_complete(self, orchestrator):
        content = "```json\n{broken}\n```\nSome text"
        status, reason, body = orchestrator._parse_verdict(content)
        assert status == "complete"
        assert body == content

    def test_json_not_verdict(self, orchestrator):
        content = '```json\n{"plan": "something", "tasks": []}\n```\nMore text'
        status, reason, body = orchestrator._parse_verdict(content)
        assert status == "complete"
        assert body == content


class TestIsSimpleGreeting:
    @pytest.mark.parametrize(
        "msg",
        [
            "hi",
            "Hello",
            "hey there",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "good morning",
            "你好",
            "谢谢",
            "bye",
        ],
    )
    def test_greetings(self, orchestrator, msg):
        assert orchestrator._is_simple_greeting(msg)

    @pytest.mark.parametrize(
        "msg",
        [
            "hi, can you help me refactor the auth module?",
            "please read the README and explain the architecture",
            "what is the purpose of client.py?",
            "a" * 31,
        ],
    )
    def test_not_greetings(self, orchestrator, msg):
        assert not orchestrator._is_simple_greeting(msg)

    def test_case_insensitive(self, orchestrator):
        assert orchestrator._is_simple_greeting("HELLO")
        assert orchestrator._is_simple_greeting("Hi")

    def test_whitespace_stripped(self, orchestrator):
        assert orchestrator._is_simple_greeting("  hi  ")


class TestIsAnalysisRequest:
    @pytest.mark.parametrize(
        "msg",
        [
            "分析一下这个代码",
            "explain how auth works",
            "analyze the performance",
            "how does the worker execute tasks?",
            "what is the purpose of this function?",
            "read the README",
            "show me the architecture",
            "describe the module",
            "review the code",
            "tell me the implementation details",
        ],
    )
    def test_analysis_requests(self, orchestrator, msg):
        assert orchestrator._is_analysis_request(msg)

    @pytest.mark.parametrize(
        "msg",
        [
            "add a new endpoint",
            "fix the bug in login",
            "refactor this function",
            "create a test file",
            "delete the old module",
        ],
    )
    def test_not_analysis(self, orchestrator, msg):
        assert not orchestrator._is_analysis_request(msg)


class TestBuildConversationSummary:
    def test_empty_conversation(self, orchestrator):
        assert orchestrator._build_conversation_summary() == ""

    def test_basic_conversation(self, orchestrator):
        orchestrator.conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        summary = orchestrator._build_conversation_summary()
        assert "[user]: Hello" in summary
        assert "[assistant]: Hi there" in summary

    def test_skips_system(self, orchestrator):
        orchestrator.conversation = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
        ]
        summary = orchestrator._build_conversation_summary()
        assert "System prompt" not in summary
        assert "[user]: Hello" in summary

    def test_truncates_long_content(self, orchestrator):
        orchestrator.conversation = [
            {"role": "user", "content": "x" * 3000},
        ]
        summary = orchestrator._build_conversation_summary()
        assert summary.endswith("...")
        assert len(summary) < 3100

    def test_respects_max_exchanges(self, orchestrator):
        orchestrator.conversation = [{"role": "user", "content": f"msg{i}"} for i in range(50)]
        summary = orchestrator._build_conversation_summary(max_exchanges=2)
        assert "msg49" in summary
        assert "msg0" not in summary

    def test_skips_empty_content(self, orchestrator):
        orchestrator.conversation = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "Hello"},
        ]
        summary = orchestrator._build_conversation_summary()
        assert "[user]" not in summary
        assert "[assistant]: Hello" in summary


class TestBuildRoundSummary:
    def test_completed_tasks(self, orchestrator):
        plan = Plan(
            description="Test plan",
            tasks=[
                Task(id="t1", description="First task"),
                Task(id="t2", description="Second task"),
            ],
        )
        plan.tasks[0].mark_completed("Result 1")
        plan.tasks[1].mark_completed("Result 2")

        summary = orchestrator._build_round_summary(plan, 1)
        assert "## Iteration 1" in summary
        assert "Test plan" in summary
        assert "[✓]" in summary
        assert "t1" in summary
        assert "Result 1" in summary

    def test_failed_tasks(self, orchestrator):
        plan = Plan(
            description="Failing plan",
            tasks=[
                Task(id="t1", description="Task that fails"),
            ],
        )
        plan.tasks[0].mark_failed("Some error")

        summary = orchestrator._build_round_summary(plan, 2)
        assert "[✗]" in summary
        assert "Some error" in summary

    def test_truncates_results(self, orchestrator):
        plan = Plan(
            description="Plan",
            tasks=[
                Task(id="t1", description="A" * 200),
            ],
        )
        plan.tasks[0].mark_completed("R" * 1000)

        summary = orchestrator._build_round_summary(plan, 1)
        assert len(summary) < 1200


class TestEstimateTokens:
    def test_empty(self, orchestrator):
        assert orchestrator._estimate_tokens() == 0

    def test_basic(self, orchestrator):
        orchestrator.conversation = [
            {"role": "user", "content": "a" * 400},
        ]
        assert orchestrator._estimate_tokens() == 100

    def test_none_content(self, orchestrator):
        orchestrator.conversation = [
            {"role": "assistant", "content": None},
        ]
        assert orchestrator._estimate_tokens() == 0


class TestOrchestratorState:
    def test_set_cwd(self, orchestrator):
        orchestrator.set_cwd("/new/path")
        assert orchestrator._cwd == "/new/path"

    def test_clear_history(self, orchestrator):
        orchestrator.conversation = [{"role": "user", "content": "hi"}]
        orchestrator._prompt_cache_loaded = True
        orchestrator.clear_history()
        assert orchestrator.conversation == []
        assert not orchestrator._prompt_cache_loaded

    def test_export_import_conversation(self, orchestrator):
        msgs = [{"role": "user", "content": "test"}]
        orchestrator.conversation = msgs.copy()
        exported = orchestrator.export_conversation()
        assert exported == msgs
        assert exported is not orchestrator.conversation

        orchestrator.clear_history()
        orchestrator.import_conversation(exported)
        assert orchestrator.conversation == msgs

    def test_set_approve_handler(self, orchestrator):
        handler = AsyncMock()
        orchestrator.set_approve_handler(handler)
        assert orchestrator._on_approve == handler

    def test_set_plan_approval_handler(self, orchestrator):
        handler = AsyncMock()
        orchestrator.set_plan_approval_handler(handler)
        assert orchestrator._on_plan_approval == handler

    def test_invalidate_prompt_cache(self, orchestrator):
        orchestrator._prompt_cache_loaded = True
        orchestrator.invalidate_prompt_cache()
        assert not orchestrator._prompt_cache_loaded


class TestGetVerdictInstruction:
    def test_basic(self, orchestrator):
        result = orchestrator._get_verdict_instruction("fix the bug")
        assert "status" in result
        assert "complete" in result
        assert "continue" in result

    def test_analysis_hint_included(self, orchestrator):
        result = orchestrator._get_verdict_instruction("explain the architecture")
        assert "code snippets" in result
        assert "architecture" in result

    def test_non_analysis_no_hint(self, orchestrator):
        result = orchestrator._get_verdict_instruction("add a button")
        assert "code snippets" not in result
