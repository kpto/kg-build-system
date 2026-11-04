"""Asset descriptors and the typed references planners consume."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg_build_system.distribution.model.public.refs import AssetRef
from kg_build_system.kernel import Key

from ..internal.dto.asset_dto import AssetDTO
from .declarations import Asset
from .options import AssetGovernance, AssetLayout, AssetSemantics


@dataclass(frozen=True, slots=True)
class AssetDescriptor:
    """A frozen, authoring-independent description of one asset.

    Example:
        ```python
        from kg_build_system import (
            AssetAuthority, AssetDescriptor, AssetGovernance, AssetSemantics,
        )

        descriptor = AssetDescriptor(
            name="open_targets",
            website=None,
            version=None,
            layout=None,
            semantics=AssetSemantics(
                subject="gene-disease associations",
                coverage="all curated evidence",
                authority=AssetAuthority.PRIMARY,
                basis="Open Targets Platform release",
            ),
            governance=AssetGovernance(),
        )
        ```
    """

    name: str
    website: str | None
    version: str | None
    layout: AssetLayout | None
    semantics: AssetSemantics
    governance: AssetGovernance


def asset_name(value: type[Asset] | AssetDescriptor | AssetDTO) -> str:
    """Return the logical name of an asset declaration or descriptor.

    Example:
        ```python
        from kg_build_system import (
            Asset, AssetAuthority, AssetOptions, AssetSemantics, asset_name,
        )

        class OpenTargets(Asset):
            options = AssetOptions(
                semantics=AssetSemantics(
                    subject="gene-disease associations",
                    coverage="all curated evidence",
                    authority=AssetAuthority.PRIMARY,
                    basis="Open Targets Platform release",
                ),
            )

        assert asset_name(OpenTargets) == "open_targets"
        ```
    """
    if isinstance(value, (AssetDescriptor, AssetDTO)):
        return value.name
    if isinstance(value, type) and issubclass(value, Asset):
        name: Any = getattr(value, "_asset_name", None)
        if isinstance(name, str) and name:
            return name
    raise TypeError(f"{value!r} is not an asset declaration or descriptor")


def asset_reference(value: type[Asset] | AssetDescriptor | AssetDTO) -> AssetRef:
    """Return the typed blueprint reference to one asset.

    Example:
        ```python
        from kg_build_system import (
            Asset, AssetAuthority, AssetOptions, AssetSemantics, asset_reference,
        )

        class OpenTargets(Asset):
            options = AssetOptions(
                semantics=AssetSemantics(
                    subject="gene-disease associations",
                    coverage="all curated evidence",
                    authority=AssetAuthority.PRIMARY,
                    basis="Open Targets Platform release",
                ),
            )

        reference = asset_reference(OpenTargets)
        assert reference.to_document() == ["asset", "asset", "open_targets"]
        ```
    """
    return AssetRef("asset", Key((asset_name(value),)))


__all__ = ["AssetDescriptor", "asset_name", "asset_reference"]
