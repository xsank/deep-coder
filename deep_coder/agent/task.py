"""Task data model for the agent system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    id: str
    description: str
    tools_needed: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    context: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=data["id"],
            description=data["description"],
            tools_needed=data.get("tools_needed", []),
            depends_on=data.get("depends_on", []),
            context=data.get("context", ""),
        )

    @property
    def is_ready(self) -> bool:
        return self.status == TaskStatus.PENDING and not self.depends_on

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING

    def mark_completed(self, result: str) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error

    def mark_retrying(self) -> None:
        self.status = TaskStatus.RETRYING
        self.retry_count += 1
        self.error = None


@dataclass
class Plan:
    description: str
    tasks: list[Task]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        return cls(
            description=data.get("plan", ""),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
        )

    def get_ready_tasks(self) -> list[Task]:
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in task.depends_on):
                ready.append(task)
        return ready

    @property
    def is_complete(self) -> bool:
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in self.tasks
        )

    @property
    def failed_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]
