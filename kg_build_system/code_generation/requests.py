"""Typed, inert generation request construction."""
from __future__ import annotations

from .models import Generation
from .providers import Provider, ProviderGenerationConfig


def generation[T: ProviderGenerationConfig](
    provider: type[Provider[T]], configuration: T, /
) -> Generation[T]:
    """Declare edit-time generation intent without performing any work.

    The call validates the provider/configuration pair and returns a frozen
    value. It does not observe a source, load data, invoke a provider or write
    a file; the assignment name is the request identity.
    """
    if not isinstance(configuration, provider.CONFIG_TYPE):
        raise TypeError(f"{provider.__name__} requires {provider.CONFIG_TYPE.__name__}")
    return Generation(provider, configuration)


__all__ = ["generation"]
