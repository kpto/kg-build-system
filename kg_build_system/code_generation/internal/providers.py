"""Typed provider implementation contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from .ir import GeneratedPackage


class ProviderGenerationConfig(BaseModel):
    """Immutable, keyword-only configuration owned by a generation provider."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


@dataclass(frozen=True, slots=True)
class ProviderContext[T: ProviderGenerationConfig]:
    """The values a provider receives for one request.

    ``project_root`` and ``request_path`` locate the author-owned project and
    its ``__init__.py``; ``request_id`` is the assignment name, and ``config``
    is the validated provider configuration.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.code_generation.internal import (
            ProviderContext, ProviderGenerationConfig,
        )

        class Config(ProviderGenerationConfig):
            source: str

        context = ProviderContext(
            Path("."), Path("contracts/__init__.py"), "people",
            Config(source="../data/people.csv"),
        )
        ```
    """

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
        remote listings); the engine tracks the request, not the observed data,
        so this runs only when a request is created, changed, or explicitly
        regenerated. A provider that reads a source schema should stamp its
        digest onto ``GeneratedPackage.source_digest`` for provenance.

        Example:
            ```python
            from kg_build_system.code_generation.internal import (
                GeneratedPackage, Provider, ProviderContext,
                ProviderGenerationConfig,
            )

            class Config(ProviderGenerationConfig):
                source: str

            class ContractProvider(Provider[Config]):
                ID = "contract"
                VERSION = "1"
                CONFIG_TYPE = Config

                @classmethod
                async def generate(
                    cls, context: ProviderContext[Config],
                ) -> GeneratedPackage:
                    return GeneratedPackage(())
            ```
        """


__all__ = ["Provider", "ProviderContext", "ProviderGenerationConfig"]
