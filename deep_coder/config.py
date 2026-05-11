"""Configuration management for Deep Coder."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


CONFIG_DIR = Path.home() / ".deep-coder"
CONFIG_FILE = CONFIG_DIR / "config.toml"
HISTORY_FILE = CONFIG_DIR / "history"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_PRO_MODEL = "deepseek-v4-pro"
DEFAULT_FLASH_MODEL = "deepseek-v4-flash"


class ModelConfig(BaseModel):
    pro_model: str = Field(default=DEFAULT_PRO_MODEL)
    flash_model: str = Field(default=DEFAULT_FLASH_MODEL)
    base_url: str = Field(default=DEFAULT_BASE_URL)
    api_key: str = Field(default="")
    max_tokens: int = Field(default=8192)
    temperature: float = Field(default=0.0)
    reasoning_effort: str = Field(default="high")


class AgentConfig(BaseModel):
    max_workers: int = Field(default=5)
    worker_timeout: int = Field(default=120)
    auto_approve_reads: bool = Field(default=True)


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    shell_allowed: bool = Field(default=True)
    approval_policy: str = Field(default="on-request")

    @classmethod
    def load(cls) -> Config:
        config = cls()
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            if "model" in data:
                config.model = ModelConfig(**{**config.model.model_dump(), **data["model"]})
            if "agent" in data:
                config.agent = AgentConfig(**{**config.agent.model_dump(), **data["agent"]})
            if "shell_allowed" in data:
                config.shell_allowed = data["shell_allowed"]
            if "approval_policy" in data:
                config.approval_policy = data["approval_policy"]
        config._apply_env_overrides()
        return config

    def _apply_env_overrides(self) -> None:
        if key := os.environ.get("DEEPSEEK_API_KEY"):
            self.model.api_key = key
        if url := os.environ.get("DEEPSEEK_BASE_URL"):
            self.model.base_url = url
        if model := os.environ.get("DEEPSEEK_PRO_MODEL"):
            self.model.pro_model = model
        if model := os.environ.get("DEEPSEEK_FLASH_MODEL"):
            self.model.flash_model = model

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = self.model_dump()
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(data, f)

    @property
    def has_api_key(self) -> bool:
        return bool(self.model.api_key.strip())


def get_config() -> Config:
    return Config.load()
