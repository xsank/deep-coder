"""Tests for the API client module."""

from __future__ import annotations

from deep_coder.client import DeepSeekClient
from deep_coder.config import Config, ModelConfig
from deep_coder.models import ModelRole


class TestDeepSeekClient:
    def test_client_creation(self):
        config = Config()
        client = DeepSeekClient(config)
        assert client.config == config

    def test_model_routing(self):
        config = Config(
            model=ModelConfig(
                pro_model="deepseek-v4-pro",
                flash_model="deepseek-v4-flash",
            )
        )
        client = DeepSeekClient(config)
        assert client._get_model_id(ModelRole.PRO) == "deepseek-v4-pro"
        assert client._get_model_id(ModelRole.FLASH) == "deepseek-v4-flash"
