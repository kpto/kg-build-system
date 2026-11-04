"""Render the asset language DTO back to authoring source.

The renderer lives in the package's private zone; this module is the internal
entry point another layer composes.
"""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.asset_dto import AssetDTO, AssetPartDTO


def render_asset_source(
    part: AssetPartDTO | AssetDTO, context: Any = None,
) -> SourceFragment:
    """Render an asset DTO as deterministic authoring source.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.model.internal import (
            AssetPartDTO,
        )
        from kg_build_system.distribution.languages.asset.service.internal import (
            render_asset_source,
        )

        assert render_asset_source(AssetPartDTO()).body == ""
        ```
    """
    from .._private.source import render_asset_source as render

    return render(part, context)


__all__ = ["render_asset_source"]
