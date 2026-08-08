"""Typed, inert generation request construction."""

from __future__ import annotations

from .models import Generation, ProviderGenerationConfig
from .providers import Provider


def generation[T: ProviderGenerationConfig](
    provider: type[Provider[T]], configuration: T, /
) -> Generation[T]:
    """Declare edit-time generation intent without performing any work."""
    if not isinstance(configuration, provider.CONFIG_TYPE):
        raise TypeError(f"{provider.__name__} requires {provider.CONFIG_TYPE.__name__}")
    return Generation(provider, configuration)
