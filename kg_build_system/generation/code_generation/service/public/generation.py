"""The inert asset-generation class decorator."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from ...model.internal.providers import ProviderGenerationConfig
from ...model.public.options import AssetGenerationOptions

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.asset import Asset

AssetT = TypeVar("AssetT", bound="Asset")
ConfigT = TypeVar("ConfigT", bound=ProviderGenerationConfig)


def asset_generation(
    options: AssetGenerationOptions[ConfigT],
) -> Callable[[type[AssetT]], type[AssetT]]:
    """Attach generation intent to an ``Asset`` subclass without doing any work.

    The decorator validates the class and stores the options as
    ``_asset_generation``. It does not read a source, import a project module,
    invoke a provider or write a file. Discovery finds the decorated class
    statically; ``generate`` reads the stored request later.

    Example:
        ```python
        from kg_build_system import Asset
        from kg_build_system.generation import (
            AssetGenerationOptions, asset_generation,
        )
        from kg_build_system.generation.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        @asset_generation(AssetGenerationOptions(
            provider=InferDataContractProvider,
            configuration=DataContractInferenceConfig(mode="source_relation"),
            package="reference_project.table",
        ))
        class Estate(Asset):
            options = ...
        ```
    """
    from .._private.generation import apply_asset_generation

    return apply_asset_generation(options)


__all__ = ["asset_generation"]
