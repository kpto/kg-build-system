"""Typed, inert generation request construction."""
from __future__ import annotations

from typing import Any

from ..internal.providers import Provider, ProviderGenerationConfig


def generation[T: ProviderGenerationConfig](
    provider: type[Provider[T]], configuration: T, /
) -> Any:
    """Declare edit-time generation intent without performing any work.

    The call validates the provider/configuration pair and returns a frozen
    value. It does not observe a source, load data, invoke a provider or write
    a file; the assignment name is the request identity.

    Example:
        ```python
        from kg_build_system.code_generation import generation
        from kg_build_system.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        request = generation(
            InferDataContractProvider,
            DataContractInferenceConfig(source="input.json", mode="table"),
        )
        ```
    """
    from .._private.requests import make_generation

    return make_generation(provider, configuration)


__all__ = ["generation"]
