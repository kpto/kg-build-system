"""Adapters from request coordinates to the provider contract."""
from __future__ import annotations

from pathlib import Path

from ..providers import (
    Provider,
    ProviderContext,
    ProviderGenerationConfig,
)


def load_provider(
    request: object,
) -> tuple[type[Provider[ProviderGenerationConfig]], ProviderGenerationConfig]:
    """Import and validate the provider and its static configuration.

    ``request`` is duck-typed on the generation-request fields so this module
    does not depend on the ownership models.
    """
    from ..._private.adapters import load_provider as implementation

    return implementation(request)


def resolve_provider_path[T: ProviderGenerationConfig](
    context: ProviderContext[T], value: str,
) -> Path:
    """Resolve a provider-owned path against the request file.

    The resolved path is an observation target, not a tracked input: it may live
    outside the project, and nothing here watches, hashes or existence-checks it.
    Fidelity to the source is enforced at runtime ingest and re-observed only by
    an explicit regeneration pass.
    """
    from ..._private.adapters import resolve_provider_path as implementation

    return implementation(context, value)


__all__ = ["load_provider", "resolve_provider_path"]
