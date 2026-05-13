"""Tests for the configuration module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from deep_coder.config import (
    DEFAULT_BASE_URL,
    DEFAULT_FLASH_MODEL,
    DEFAULT_PRO_MODEL,
    AgentConfig,
    Config,
    ModelConfig,
)


class TestModelConfig:
    def test_defaults(self):
        mc = ModelConfig()
        assert mc.pro_model == DEFAULT_PRO_MODEL
        assert mc.flash_model == DEFAULT_FLASH_MODEL
        assert mc.base_url == DEFAULT_BASE_URL
        assert mc.api_key == ""
        assert mc.max_tokens == 16384
        assert mc.temperature == 0.0

    def test_custom_values(self):
        mc = ModelConfig(pro_model="my-pro", api_key="sk-test")
        assert mc.pro_model == "my-pro"
        assert mc.api_key == "sk-test"


class TestAgentConfig:
    def test_defaults(self):
        ac = AgentConfig()
        assert ac.max_workers == 5
        assert ac.worker_timeout == 120
        assert ac.auto_approve_reads is True
        assert ac.max_iterations == 3


class TestConfig:
    def test_defaults(self):
        config = Config()
        assert config.shell_allowed is True
        assert config.approval_policy == "on-request"
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.agent, AgentConfig)

    def test_has_api_key_empty(self):
        config = Config()
        assert config.has_api_key is False

    def test_has_api_key_whitespace(self):
        config = Config(model=ModelConfig(api_key="   "))
        assert config.has_api_key is False

    def test_has_api_key_set(self):
        config = Config(model=ModelConfig(api_key="sk-abc123"))
        assert config.has_api_key is True

    def test_apply_toml(self):
        with tempfile.TemporaryDirectory() as d:
            toml_path = Path(d) / "config.toml"
            toml_path.write_text(
                '[model]\napi_key = "from-toml"\nmax_tokens = 4096\n[agent]\nmax_workers = 3\n'
            )
            config = Config()
            Config._apply_toml(config, toml_path)
            assert config.model.api_key == "from-toml"
            assert config.model.max_tokens == 4096
            assert config.agent.max_workers == 3
            assert config.model.pro_model == DEFAULT_PRO_MODEL

    def test_apply_toml_partial(self):
        with tempfile.TemporaryDirectory() as d:
            toml_path = Path(d) / "config.toml"
            toml_path.write_text("shell_allowed = false\n")
            config = Config()
            Config._apply_toml(config, toml_path)
            assert config.shell_allowed is False
            assert config.model.api_key == ""

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
        monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://custom.api")
        monkeypatch.setenv("DEEPSEEK_PRO_MODEL", "env-pro")
        monkeypatch.setenv("DEEPSEEK_FLASH_MODEL", "env-flash")
        config = Config()
        config._apply_env_overrides()
        assert config.model.api_key == "env-key"
        assert config.model.base_url == "https://custom.api"
        assert config.model.pro_model == "env-pro"
        assert config.model.flash_model == "env-flash"

    def test_env_overrides_partial(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
        monkeypatch.setenv("DEEPSEEK_PRO_MODEL", "custom-pro")
        config = Config()
        config._apply_env_overrides()
        assert config.model.api_key == ""
        assert config.model.base_url == DEFAULT_BASE_URL
        assert config.model.pro_model == "custom-pro"

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            config = Config(
                model=ModelConfig(api_key="test-key", max_tokens=2048),
                agent=AgentConfig(max_workers=2),
            )
            original_cwd = os.getcwd()
            try:
                os.chdir(d)
                config.save(local=True)
                config_file = Path(d) / ".deep-coder" / "config.toml"
                assert config_file.exists()
                reloaded = Config()
                Config._apply_toml(reloaded, config_file)
                assert reloaded.model.api_key == "test-key"
                assert reloaded.model.max_tokens == 2048
                assert reloaded.agent.max_workers == 2
            finally:
                os.chdir(original_cwd)
