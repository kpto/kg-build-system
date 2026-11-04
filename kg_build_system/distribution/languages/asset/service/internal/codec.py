"""Canonical document codec interface for the asset blueprint part.

The codec itself lives in the package's private zone; this module is the internal
entry point another layer composes.
"""
from __future__ import annotations

from typing import Any

from ...model.internal.dto.asset_dto import AssetPartDTO


def assets_to_document(part: AssetPartDTO) -> list[dict[str, Any]]:
    """Encode the asset part as an array of JSON-compatible objects.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.model.internal import (
            AssetPartDTO,
        )
        from kg_build_system.distribution.languages.asset.service.internal import (
            assets_to_document,
        )

        assert assets_to_document(AssetPartDTO()) == []
        ```
    """
    from .._private.codec import assets_to_document as encode

    return encode(part)


def assets_from_document(value: Any) -> AssetPartDTO:
    """Rebuild the asset part from its JSON-compatible array.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.service.internal import (
            assets_from_document,
        )

        assert assets_from_document([]).assets == ()
        ```
    """
    from .._private.codec import assets_from_document as decode

    return decode(value)


__all__ = ["assets_from_document", "assets_to_document"]
