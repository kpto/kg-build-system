"""Author-facing request attached to an asset declaration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..internal.providers import Provider, ProviderGenerationConfig

ConfigT = TypeVar("ConfigT", bound=ProviderGenerationConfig)


@dataclass(frozen=True, slots=True)
class AssetContractOptions(Generic[ConfigT]):
    """The generation-only values one asset contract declares.

    ``provider`` is the implementation that observes the source,
    ``configuration`` is its validated configuration, and ``package`` is the
    import package that receives the generated product. The asset's name is the
    request identity and the product is ``package/<asset name>``. None of these
    values belongs to ``AssetOptions`` or the blueprint DTO: an asset states its
    data, a contract states how its table declarations are generated.

    Example:
        ```python
        from kg_build_system.generation import AssetContractOptions
        from kg_build_system.generation.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        options = AssetContractOptions(
            provider=InferDataContractProvider,
            configuration=DataContractInferenceConfig(mode="table"),
            package="reference_project.table",
        )
        ```
    """

    provider: type[Provider[Any]]
    configuration: ConfigT
    package: str


__all__ = ["AssetContractOptions"]
