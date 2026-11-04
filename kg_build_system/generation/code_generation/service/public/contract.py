"""The inert asset-contract class decorator."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from ...model.public.contract import AssetContractOptions

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.asset import Asset

AssetT = TypeVar("AssetT", bound="Asset")


def asset_contract(
    options: AssetContractOptions[Any],
) -> Callable[[type[AssetT]], type[AssetT]]:
    """Attach generation intent to an ``Asset`` subclass without doing any work.

    The decorator validates the class and stores the options as
    ``_asset_contract``. It does not read a source, import a project module,
    invoke a provider or write a file. Discovery finds the decorated class
    statically; ``generate`` reads the stored request later.

    Example:
        ```python
        from kg_build_system import Asset
        from kg_build_system.generation import (
            AssetContractOptions, asset_contract,
        )
        from kg_build_system.generation.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        @asset_contract(AssetContractOptions(
            provider=InferDataContractProvider,
            configuration=DataContractInferenceConfig(mode="table"),
            package="reference_project.table",
        ))
        class Estate(Asset):
            options = ...
        ```
    """
    from .._private.contract import apply_asset_contract

    return apply_asset_contract(options)


__all__ = ["asset_contract"]
