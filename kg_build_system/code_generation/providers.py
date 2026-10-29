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
    async def generate(cls, context: ProviderContext[T]) -> GeneratedPackage:
        """Observe the configured source(s) and produce the package once.

        The provider may read whatever it needs (schema metadata, samples,
        remote listings); the engine tracks the request, not the observed
        data, so this runs only when a request is created, changed, or
        explicitly regenerated. A provider that reads a source schema should
        stamp its digest onto ``GeneratedPackage.source_digest`` for
        provenance.
        """


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


def resolve_provider_path(context: ProviderContext[ProviderGenerationConfig], value: str) -> Path:
    """Resolve a provider-owned path against the request file.

    The resolved path is an observation target, not a tracked input: it may live
    outside the project, and nothing here watches, hashes or existence-checks it.
    Fidelity to the source is enforced at runtime ingest and re-observed only by
    an explicit regeneration pass.
    """
    return (context.request_path.parent / value).resolve()
