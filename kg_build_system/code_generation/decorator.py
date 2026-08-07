"""Runtime identity decorator used as the static generation marker."""

from __future__ import annotations

from collections.abc import Callable

from .models import ProviderGenerationConfig
from .providers import Provider


def generated[T: ProviderGenerationConfig, D](
    provider_type: type[Provider[T]], config: T, /
) -> Callable[[D], D]:
    """Mark a declaration for edit-time generation without mutating its shape."""

    if not isinstance(config, provider_type.CONFIG_TYPE):
        raise TypeError(f"{provider_type.__name__} requires {provider_type.CONFIG_TYPE.__name__}")

    def decorate(declaration: D) -> D:
        setattr(declaration, "__kbs_generation__", (provider_type, config))
        return declaration
    return decorate
