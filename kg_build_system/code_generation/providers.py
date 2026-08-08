"""Typed provider implementation contract and loading."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import ClassVar, cast

from .models import GeneratedPackage, GenerationRequest, ProviderGenerationConfig


@dataclass(frozen=True, slots=True)
class ProviderContext[T: ProviderGenerationConfig]:
    project_root: Path
    request_path: Path
    request_id: str
    config: T

    def resolve_path(self, value: str) -> Path:
        """Resolve a provider-owned project path without assigning it semantics."""
        path = (self.request_path.parent / value).resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError as error:
            raise ValueError(f"code-generation path is outside the project: {path}") from error
        return path


class Provider[T: ProviderGenerationConfig](ABC):
    """Base class for typed edit-time generation providers."""

    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]]

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        config_type = cls.__dict__.get("CONFIG_TYPE")
        if not isinstance(config_type, type) or not issubclass(config_type, ProviderGenerationConfig):
            raise TypeError("provider implementations must declare a ProviderGenerationConfig CONFIG_TYPE")

    @classmethod
    @abstractmethod
    async def dependencies(cls, context: ProviderContext[T]) -> tuple[Path, ...]: ...

    @classmethod
    @abstractmethod
    async def generate(cls, context: ProviderContext[T]) -> GeneratedPackage: ...


def _load_class(module_name: str, qualname: str) -> type[object]:
    value: object = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise TypeError(f"{module_name}.{qualname} is not a class")
    return value


def load_provider(
    request: GenerationRequest,
) -> tuple[type[Provider[ProviderGenerationConfig]], ProviderGenerationConfig]:
    provider_type = _load_class(request.provider_module, request.provider_qualname)
    if not issubclass(provider_type, Provider):
        raise TypeError(
            f"{request.provider_module}.{request.provider_qualname} is not a code-generation Provider"
        )
    if not provider_type.ID or not provider_type.VERSION:
        raise ValueError("providers require non-empty ID and VERSION values")
    config_type = _load_class(request.config_module, request.config_qualname)
    if config_type is not provider_type.CONFIG_TYPE:
        expected = f"{provider_type.CONFIG_TYPE.__module__}.{provider_type.CONFIG_TYPE.__qualname__}"
        raise TypeError(f"provider configuration must be constructed with {expected}")
    config = provider_type.CONFIG_TYPE.model_validate(request.configuration)
    return cast(type[Provider[ProviderGenerationConfig]], provider_type), config
