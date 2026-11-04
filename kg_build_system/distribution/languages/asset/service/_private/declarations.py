"""Prepare an ``Asset`` subclass for discovery and transcription."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.service.internal.rendering import snake_case

from ...model.public.options import AssetOptions


def prepare_asset_declaration(cls: type[Any]) -> None:
    """Validate and record the options and name of an asset subclass."""
    options = vars(cls).get("options")
    if not isinstance(options, AssetOptions):
        raise TypeError(
            f"asset {cls.__name__!r} must declare options = AssetOptions(...)"
        )
    name = options.name or snake_case(cls.__name__)
    if not name:
        raise ValueError(f"asset {cls.__name__!r} has no usable name")
    cls._asset_options = options
    cls._asset_name = name


def is_asset_declaration(value: Any) -> bool:
    """Whether a value is a concrete ``Asset`` subclass."""
    from ...model.public.declarations import Asset

    return (
        isinstance(value, type)
        and issubclass(value, Asset)
        and value is not Asset
        and "_asset_options" in vars(value)
    )


__all__ = ["is_asset_declaration", "prepare_asset_declaration"]
