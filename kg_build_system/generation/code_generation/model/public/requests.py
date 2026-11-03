"""Author-facing generation request values."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from ..internal.providers import ProviderGenerationConfig
from .values import StaticValue

ConfigT = TypeVar("ConfigT", bound=ProviderGenerationConfig)


@dataclass(frozen=True, slots=True)
class Generation(Generic[ConfigT]):
    """An inert, typed edit-time generation request.

    Create it with :func:`kg_build_system.generation.code_generation.generation`; the
    assignment name is the request identity. It holds a provider class and its
    validated configuration, and performs no observation or writes.

    Example:
        ```python
        from kg_build_system.generation.code_generation import generation
        from kg_build_system.generation.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        people = generation(
            InferDataContractProvider,
            DataContractInferenceConfig(
                source="../data/people.csv", mode="table",
            ),
        )
        ```
    """

    provider: type[object]
    configuration: ConfigT


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """A statically discovered request attached to one public declaration.

    The provider and configuration are stored as import coordinates, so
    discovery never imports the author-owned package. ``configuration`` holds
    the static literal keyword arguments, validated into the provider's
    ``CONFIG_TYPE`` when generation runs.

    Example:
        ```python
        from kg_build_system.generation.code_generation import GenerationRequest

        request = GenerationRequest(
            "project.providers", "PeopleProvider",
            "project.providers", "PeopleConfiguration",
            {"source": "../data/people.csv"},
        )
        ```
    """

    provider_module: str
    provider_qualname: str
    config_module: str
    config_qualname: str
    configuration: dict[str, StaticValue] = field(default_factory=dict)


__all__ = ["Generation", "GenerationRequest"]
