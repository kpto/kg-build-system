"""Provider loading and path resolution for request adapters."""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast

from ...model.internal.providers import (
    Provider,
    ProviderContext,
    ProviderGenerationConfig,
)
from ...model.public.requests import GenerationRequest


def _load_class(module_name: str, qualname: str) -> type[object]:
    value: object = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise TypeError(f"{module_name}.{qualname} is not a class")
    return value


def load_provider(
    request: object,
) -> tuple[type[Provider[ProviderGenerationConfig]], ProviderGenerationConfig]:
    """Import and validate the provider and its static configuration.

    ``request`` is duck-typed on the generation-request fields so this module
    does not depend on the ownership models.
    """
    if not isinstance(request, GenerationRequest):
        raise TypeError("load_provider requires a GenerationRequest")
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


def resolve_provider_path[T: ProviderGenerationConfig](
    context: ProviderContext[T], value: str,
) -> Path:
    """Resolve a provider-owned path against the request file.

    The resolved path is an observation target, not a tracked input: it may live
    outside the project, and nothing here watches, hashes or existence-checks it.
    Fidelity to the source is enforced at runtime ingest and re-observed only by
    an explicit regeneration pass.
    """
    return (context.request_path.parent / value).resolve()


__all__ = ["load_provider", "resolve_provider_path"]
