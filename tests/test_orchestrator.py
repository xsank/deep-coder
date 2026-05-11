"""Tests for the orchestrator and task system."""

from __future__ import annotations

import json

from deep_coder.agent.task import Plan, Task, TaskStatus


class TestTask:
    def test_from_dict(self):
        data = {
            "id": "task_1",
            "description": "Read the README",
            "tools_needed": ["read_file"],
            "depends_on": [],
            "context": "Check project structure",
        }
        task = Task.from_dict(data)
        assert task.id == "task_1"
        assert task.description == "Read the README"
        assert task.tools_needed == ["read_file"]
        assert task.status == TaskStatus.PENDING

    def test_task_lifecycle(self):
        task = Task(id="t1", description="test")
        assert task.is_ready
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        task.mark_completed("done")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "done"

    def test_task_failure(self):
        task = Task(id="t1", description="test")
        task.mark_failed("something broke")
        assert task.status == TaskStatus.FAILED
        assert task.error == "something broke"


class TestPlan:
    def test_from_dict(self):
        data = {
            "plan": "Test plan",
            "tasks": [
                {"id": "t1", "description": "First task"},
                {"id": "t2", "description": "Second task", "depends_on": ["t1"]},
            ],
        }
        plan = Plan.from_dict(data)
        assert plan.description == "Test plan"
        assert len(plan.tasks) == 2

    def test_ready_tasks_with_deps(self):
        data = {
            "plan": "Test",
            "tasks": [
                {"id": "t1", "description": "First"},
                {"id": "t2", "description": "Second", "depends_on": ["t1"]},
                {"id": "t3", "description": "Third"},
            ],
        }
        plan = Plan.from_dict(data)
        ready = plan.get_ready_tasks()
        ready_ids = [t.id for t in ready]
        assert "t1" in ready_ids
        assert "t3" in ready_ids
        assert "t2" not in ready_ids

    def test_ready_after_dep_completed(self):
        data = {
            "plan": "Test",
            "tasks": [
                {"id": "t1", "description": "First"},
                {"id": "t2", "description": "Second", "depends_on": ["t1"]},
            ],
        }
        plan = Plan.from_dict(data)
        plan.tasks[0].mark_completed("done")
        ready = plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "t2"

    def test_is_complete(self):
        data = {
            "plan": "Test",
            "tasks": [
                {"id": "t1", "description": "First"},
                {"id": "t2", "description": "Second"},
            ],
        }
        plan = Plan.from_dict(data)
        assert not plan.is_complete
        plan.tasks[0].mark_completed("ok")
        assert not plan.is_complete
        plan.tasks[1].mark_completed("ok")
        assert plan.is_complete

    def test_failed_tasks(self):
        data = {
            "plan": "Test",
            "tasks": [
                {"id": "t1", "description": "First"},
                {"id": "t2", "description": "Second"},
            ],
        }
        plan = Plan.from_dict(data)
        plan.tasks[0].mark_completed("ok")
        plan.tasks[1].mark_failed("error")
        assert plan.is_complete
        assert len(plan.failed_tasks) == 1
        assert plan.failed_tasks[0].id == "t2"
