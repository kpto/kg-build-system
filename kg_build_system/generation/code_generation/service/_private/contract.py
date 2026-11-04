"""Validation and application of an inert asset contract."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from ...model.internal.providers import Provider
from ...model.public.contract import AssetContractOptions

AssetT = TypeVar("AssetT")


def _validate_package(package: str) -> None:
    if not isinstance(package, str) or not package:
        raise TypeError("asset contract package must be a non-empty string")
    parts = package.split(".")
    if any(not part.isidentifier() for part in parts):
        raise ValueError(f"asset contract package is not a dotted identifier: {package!r}")


def apply_asset_contract(
    options: AssetContractOptions[Any],
) -> Callable[[type[AssetT]], type[AssetT]]:
    """Validate one contract and return the decorator that stores it."""
    from kg_build_system.distribution.languages.asset import Asset

    if not isinstance(options, AssetContractOptions):
        raise TypeError("asset_contract requires AssetContractOptions")
    if not isinstance(options.provider, type) or not issubclass(options.provider, Provider):
        raise TypeError("asset contract provider must be a code-generation Provider")
    if not isinstance(options.configuration, options.provider.CONFIG_TYPE):
        raise TypeError(
            f"{options.provider.__name__} requires {options.provider.CONFIG_TYPE.__name__}"
        )
    _validate_package(options.package)

    def decorate(cls: type[AssetT]) -> type[AssetT]:
        if not isinstance(cls, type) or not issubclass(cls, Asset):
            raise TypeError("@asset_contract can only decorate an Asset subclass")
        setattr(cls, "_asset_contract", options)
        return cls

    return decorate


__all__ = ["apply_asset_contract"]
