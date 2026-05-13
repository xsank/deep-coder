"""Tests for config.py — load, save, env overrides, _find_local_config."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from deep_coder.config import Config, ModelConfig, _find_local_config


class TestFindLocalConfig:
    def test_no_config_found(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("deep_coder.config.Path.cwd", return_value=Path(d)):
                result = _find_local_config()
                assert result is None

    def test_finds_config_in_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / ".deep-coder"
            config_dir.mkdir()
            config_file = config_dir / "config.toml"
            config_file.write_text("")
            with patch("deep_coder.config.Path.cwd", return_value=Path(d)):
                result = _find_local_config()
                assert result is not None
                assert result == config_file

    def test_stops_at_git_root(self):
        with tempfile.TemporaryDirectory() as d:
            git_dir = Path(d) / ".git"
            git_dir.mkdir()
            with patch("deep_coder.config.Path.cwd", return_value=Path(d)):
                result = _find_local_config()
                assert result is None


class TestConfigApplyToml:
    def test_apply_model_config(self):
        with tempfile.TemporaryDirectory() as d:
            config_file = Path(d) / "config.toml"
            config_file.write_bytes(
                b'[model]\napi_key = "test-key"\nbase_url = "https://custom.api"\n'
            )
            config = Config()
            Config._apply_toml(config, config_file)
            assert config.model.api_key == "test-key"
            assert config.model.base_url == "https://custom.api"

    def test_apply_agent_config(self):
        with tempfile.TemporaryDirectory() as d:
            config_file = Path(d) / "config.toml"
            config_file.write_bytes(b"[agent]\nmax_workers = 10\nworker_timeout = 60\n")
            config = Config()
            Config._apply_toml(config, config_file)
            assert config.agent.max_workers == 10
            assert config.agent.worker_timeout == 60

    def test_apply_top_level_fields(self):
        with tempfile.TemporaryDirectory() as d:
            config_file = Path(d) / "config.toml"
            config_file.write_bytes(b'shell_allowed = false\napproval_policy = "always"\n')
            config = Config()
            Config._apply_toml(config, config_file)
            assert config.shell_allowed is False
            assert config.approval_policy == "always"


class TestConfigLoad:
    def test_load_default(self):
        with patch("deep_coder.config.GLOBAL_CONFIG_FILE") as mock_global:
            mock_global.exists.return_value = False
            with patch("deep_coder.config._find_local_config", return_value=None):
                config = Config.load()
                assert config.model.api_key == ""
                assert config.agent.max_workers == 5


class TestConfigEnvOverrides:
    def test_api_key_from_env(self):
        config = Config()
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env-key"}, clear=False):
            config._apply_env_overrides()
            assert config.model.api_key == "env-key"

    def test_base_url_from_env(self):
        config = Config()
        with patch.dict(os.environ, {"DEEPSEEK_BASE_URL": "https://env.api"}, clear=False):
            config._apply_env_overrides()
            assert config.model.base_url == "https://env.api"

    def test_model_names_from_env(self):
        config = Config()
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_PRO_MODEL": "custom-pro",
                "DEEPSEEK_FLASH_MODEL": "custom-flash",
            },
            clear=False,
        ):
            config._apply_env_overrides()
            assert config.model.pro_model == "custom-pro"
            assert config.model.flash_model == "custom-flash"


class TestConfigSave:
    def test_save_global(self):
        with tempfile.TemporaryDirectory() as d:
            config = Config(model=ModelConfig(api_key="save-test"))
            with patch("deep_coder.config.GLOBAL_CONFIG_DIR", Path(d)):
                config.save(local=False)
                config_file = Path(d) / "config.toml"
                assert config_file.exists()
                content = config_file.read_bytes()
                assert b"save-test" in content

    def test_save_local(self):
        with tempfile.TemporaryDirectory() as d:
            config = Config()
            with patch("deep_coder.config.Path.cwd", return_value=Path(d)):
                config.save(local=True)
                config_file = Path(d) / ".deep-coder" / "config.toml"
                assert config_file.exists()


class TestHasApiKey:
    def test_empty_key(self):
        config = Config()
        assert config.has_api_key is False

    def test_whitespace_key(self):
        config = Config(model=ModelConfig(api_key="  "))
        assert config.has_api_key is False

    def test_valid_key(self):
        config = Config(model=ModelConfig(api_key="sk-test"))
        assert config.has_api_key is True
