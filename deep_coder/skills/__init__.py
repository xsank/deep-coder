"""Developer skills registry."""

from __future__ import annotations

from typing import Optional

from deep_coder.skills.base import Skill


class SkillRegistry:
    """Registry for developer skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())


def create_default_skills() -> SkillRegistry:
    from deep_coder.skills.commit import CommitSkill
    from deep_coder.skills.explain import ExplainSkill
    from deep_coder.skills.fix import FixSkill
    from deep_coder.skills.memory import MemorySkill, RememberSkill
    from deep_coder.skills.pr import PRSkill
    from deep_coder.skills.review import ReviewSkill
    from deep_coder.skills.test_skill import TestSkill
    from deep_coder.skills.think import ThinkSkill

    registry = SkillRegistry()
    registry.register(ReviewSkill())
    registry.register(CommitSkill())
    registry.register(TestSkill())
    registry.register(FixSkill())
    registry.register(ThinkSkill())
    registry.register(PRSkill())
    registry.register(ExplainSkill())
    registry.register(RememberSkill())
    registry.register(MemorySkill())
    return registry
