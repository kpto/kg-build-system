"""The concrete asset declaration an author writes."""
from __future__ import annotations

from typing import Any, ClassVar

from .options import AssetOptions


class Asset:
    """Base class for one logical unit of source data.

    Declare an asset by subclassing ``Asset`` and assigning ``options``. The
    asset's name defaults to the class name in snake case. A concrete asset is
    terminal: it may not be re-declared as another asset with inherited options.

    Example:
        ```python
        from kg_build_system import (
            Asset, AssetAuthority, AssetOptions, AssetSemantics,
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
        ```
    """

    options: ClassVar[AssetOptions]
    _asset_options: ClassVar[AssetOptions]
    _asset_name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import prepare_asset_declaration

        prepare_asset_declaration(cls)


__all__ = ["Asset"]
