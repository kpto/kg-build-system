"""Author-facing generation request attached to an asset declaration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from ..internal.providers import Provider, ProviderGenerationConfig

ConfigT = TypeVar("ConfigT", bound=ProviderGenerationConfig)


@dataclass(frozen=True, slots=True)
class AssetGenerationOptions(Generic[ConfigT]):
    """The generation-only values one asset generation request declares.

    ``provider`` is the implementation that observes the source,
    ``configuration`` is its validated configuration, and ``package`` is the
    import package that receives the generated product. The asset's name is the
    request identity and the product is ``package/<asset name>``. None of these
    values belongs to ``AssetOptions`` or the blueprint DTO: an asset states its
    data, a generation request states how its source relation declarations are
    generated.

    Example:
        ```python
        from kg_build_system.generation import AssetGenerationOptions
        from kg_build_system.generation.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        options = AssetGenerationOptions(
            provider=InferDataContractProvider,
            configuration=DataContractInferenceConfig(mode="source_relation"),
            package="reference_project.table",
        )
        ```
    """

    provider: type[Provider[ConfigT]]
    configuration: ConfigT
    package: str


__all__ = ["AssetGenerationOptions"]
