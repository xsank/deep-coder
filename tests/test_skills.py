"""Tests for skills — base class and individual skill properties."""

from __future__ import annotations

from deep_coder.skills.commit import CommitSkill
from deep_coder.skills.explain import ExplainSkill
from deep_coder.skills.fix import FixSkill
from deep_coder.skills.pr import PRSkill
from deep_coder.skills.review import ReviewSkill
from deep_coder.skills.test_skill import TestSkill
from deep_coder.skills.think import ThinkSkill


class TestSkillProperties:
    def test_review_skill(self):
        skill = ReviewSkill()
        assert skill.name == "/review"
        assert "review" in skill.description.lower()
        assert "/review" in skill.usage

    def test_commit_skill(self):
        skill = CommitSkill()
        assert skill.name == "/commit"
        assert "commit" in skill.description.lower()
        assert "/commit" in skill.usage

    def test_test_skill(self):
        skill = TestSkill()
        assert skill.name == "/test"
        assert "test" in skill.description.lower()
        assert "/test" in skill.usage

    def test_fix_skill(self):
        skill = FixSkill()
        assert skill.name == "/fix"
        assert "fix" in skill.description.lower()
        assert "/fix" in skill.usage

    def test_think_skill(self):
        skill = ThinkSkill()
        assert skill.name == "/think"
        assert "think" in skill.description.lower() or "reason" in skill.description.lower()
        assert "/think" in skill.usage

    def test_pr_skill(self):
        skill = PRSkill()
        assert skill.name == "/pr"
        assert "/pr" in skill.usage

    def test_explain_skill(self):
        skill = ExplainSkill()
        assert skill.name == "/explain"
        assert "explain" in skill.description.lower()
        assert "/explain" in skill.usage


class TestSkillsInit:
    def test_create_default_skills(self):
        from deep_coder.skills import create_default_skills

        registry = create_default_skills()
        skills = registry.list_skills()
        names = {s.name for s in skills}
        assert "/review" in names
        assert "/commit" in names
        assert "/test" in names
        assert "/fix" in names
        assert "/think" in names
        assert "/pr" in names
        assert "/explain" in names

    def test_skill_registry_get(self):
        from deep_coder.skills import create_default_skills

        registry = create_default_skills()
        assert registry.get("/review") is not None
        assert registry.get("/nonexistent") is None
