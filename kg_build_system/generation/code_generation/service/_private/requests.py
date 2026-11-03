"""Request construction implementation for the public generation function."""
from __future__ import annotations

from typing import Any

from ...model.internal.providers import Provider
from ...model.public.requests import Generation


def make_generation(provider: type[Provider[Any]], configuration: Any) -> Any:
    """Validate a provider/configuration pair and freeze the request."""
    if not isinstance(configuration, provider.CONFIG_TYPE):
        raise TypeError(
            f"{provider.__name__} requires {provider.CONFIG_TYPE.__name__}"
        )
    return Generation(provider, configuration)


__all__ = ["make_generation"]
