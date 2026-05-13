"""Extended tests for agent/task.py — retry, edge cases."""

from __future__ import annotations

from deep_coder.agent.task import Plan, Task, TaskStatus


class TestTaskRetry:
    def test_mark_retrying(self):
        task = Task(id="t1", description="test")
        task.mark_failed("error")
        assert task.status == TaskStatus.FAILED
        assert task.error == "error"

        task.mark_retrying()
        assert task.status == TaskStatus.RETRYING
        assert task.retry_count == 1
        assert task.error is None

    def test_retry_increments(self):
        task = Task(id="t1", description="test")
        task.mark_retrying()
        task.mark_retrying()
        assert task.retry_count == 2

    def test_is_ready_with_deps(self):
        task = Task(id="t1", description="test", depends_on=["t0"])
        assert not task.is_ready

    def test_is_ready_after_running(self):
        task = Task(id="t1", description="test")
        task.mark_running()
        assert not task.is_ready

    def test_from_dict_minimal(self):
        data = {"id": "t1", "description": "Do something"}
        task = Task.from_dict(data)
        assert task.tools_needed == []
        assert task.depends_on == []
        assert task.context == ""


class TestPlanEdgeCases:
    def test_empty_plan(self):
        plan = Plan.from_dict({"plan": "Empty", "tasks": []})
        assert plan.is_complete
        assert plan.get_ready_tasks() == []
        assert plan.failed_tasks == []

    def test_all_failed(self):
        plan = Plan.from_dict(
            {
                "plan": "Fail",
                "tasks": [
                    {"id": "t1", "description": "A"},
                    {"id": "t2", "description": "B"},
                ],
            }
        )
        plan.tasks[0].mark_failed("e1")
        plan.tasks[1].mark_failed("e2")
        assert plan.is_complete
        assert len(plan.failed_tasks) == 2

    def test_diamond_dependency(self):
        plan = Plan.from_dict(
            {
                "plan": "Diamond",
                "tasks": [
                    {"id": "t1", "description": "Root"},
                    {"id": "t2", "description": "Left", "depends_on": ["t1"]},
                    {"id": "t3", "description": "Right", "depends_on": ["t1"]},
                    {"id": "t4", "description": "Join", "depends_on": ["t2", "t3"]},
                ],
            }
        )
        ready = plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "t1"

        plan.tasks[0].mark_completed("done")
        ready = plan.get_ready_tasks()
        ids = {t.id for t in ready}
        assert ids == {"t2", "t3"}
        assert "t4" not in ids

        plan.tasks[1].mark_completed("done")
        ready = plan.get_ready_tasks()
        ready_ids = {t.id for t in ready}
        assert "t4" not in ready_ids  # t4 still waiting on t3

        plan.tasks[2].mark_completed("done")
        ready = plan.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "t4"

    def test_no_plan_key(self):
        plan = Plan.from_dict({"tasks": [{"id": "t1", "description": "A"}]})
        assert plan.description == ""

    def test_running_not_complete(self):
        plan = Plan.from_dict(
            {
                "plan": "Running",
                "tasks": [{"id": "t1", "description": "A"}],
            }
        )
        plan.tasks[0].mark_running()
        assert not plan.is_complete
