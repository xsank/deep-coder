"""Tests for the model registry."""

from __future__ import annotations

from deep_coder.models import ModelInfo, ModelRegistry, ModelRole, get_registry


class TestModelRole:
    def test_enum_values(self):
        assert ModelRole.PRO == "pro"
        assert ModelRole.FLASH == "flash"


class TestModelInfo:
    def test_defaults(self):
        info = ModelInfo(id="test-model", role=ModelRole.PRO)
        assert info.supports_tools is True
        assert info.supports_reasoning is True
        assert info.aliases == []


class TestModelRegistry:
    def test_resolve_by_name(self):
        reg = ModelRegistry()
        info = reg.resolve(name="deepseek-v4-pro")
        assert info.id == "deepseek-v4-pro"
        assert info.role == ModelRole.PRO

    def test_resolve_by_alias(self):
        reg = ModelRegistry()
        info = reg.resolve(name="pro")
        assert info.id == "deepseek-v4-pro"

    def test_resolve_case_insensitive(self):
        reg = ModelRegistry()
        info = reg.resolve(name="PRO")
        assert info.id == "deepseek-v4-pro"

    def test_resolve_flash_alias(self):
        reg = ModelRegistry()
        for alias in ["flash", "deepseek-flash", "deepseek-chat", "deepseek-reasoner"]:
            info = reg.resolve(name=alias)
            assert info.id == "deepseek-v4-flash"

    def test_resolve_by_role(self):
        reg = ModelRegistry()
        pro = reg.resolve(role=ModelRole.PRO)
        flash = reg.resolve(role=ModelRole.FLASH)
        assert pro.role == ModelRole.PRO
        assert flash.role == ModelRole.FLASH

    def test_resolve_unknown_returns_default(self):
        reg = ModelRegistry()
        info = reg.resolve(name="nonexistent-model")
        assert info.id == "deepseek-v4-pro"

    def test_resolve_no_args_returns_default(self):
        reg = ModelRegistry()
        info = reg.resolve()
        assert info.id == "deepseek-v4-pro"

    def test_get_pro(self):
        reg = ModelRegistry()
        assert reg.get_pro().role == ModelRole.PRO

    def test_get_flash(self):
        reg = ModelRegistry()
        assert reg.get_flash().role == ModelRole.FLASH

    def test_list_models(self):
        reg = ModelRegistry()
        models = reg.list_models()
        assert len(models) == 2
        ids = {m.id for m in models}
        assert "deepseek-v4-pro" in ids
        assert "deepseek-v4-flash" in ids

    def test_get_registry_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2
