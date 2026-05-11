"""Model definitions and registry for DeepSeek V4 models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModelRole(str, Enum):
    PRO = "pro"
    FLASH = "flash"


@dataclass
class ModelInfo:
    id: str
    role: ModelRole
    supports_tools: bool = True
    supports_reasoning: bool = True
    aliases: list[str] = field(default_factory=list)


class ModelRegistry:
    def __init__(self) -> None:
        self._models: list[ModelInfo] = [
            ModelInfo(
                id="deepseek-v4-pro",
                role=ModelRole.PRO,
                supports_tools=True,
                supports_reasoning=True,
                aliases=["pro", "deepseek-pro"],
            ),
            ModelInfo(
                id="deepseek-v4-flash",
                role=ModelRole.FLASH,
                supports_tools=True,
                supports_reasoning=True,
                aliases=["flash", "deepseek-flash", "deepseek-chat", "deepseek-reasoner"],
            ),
        ]
        self._alias_map: dict[str, int] = {}
        for idx, model in enumerate(self._models):
            self._alias_map[model.id.lower()] = idx
            for alias in model.aliases:
                self._alias_map[alias.lower()] = idx

    def resolve(self, name: Optional[str] = None, role: Optional[ModelRole] = None) -> ModelInfo:
        if name:
            key = name.strip().lower()
            if key in self._alias_map:
                return self._models[self._alias_map[key]]
        if role:
            for model in self._models:
                if model.role == role:
                    return model
        return self._models[0]

    def get_pro(self) -> ModelInfo:
        return self.resolve(role=ModelRole.PRO)

    def get_flash(self) -> ModelInfo:
        return self.resolve(role=ModelRole.FLASH)

    def list_models(self) -> list[ModelInfo]:
        return list(self._models)


_registry = ModelRegistry()


def get_registry() -> ModelRegistry:
    return _registry
