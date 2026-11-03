"""Canonical document codec interface for the table language blueprint part.

The codec itself lives in the package's private zone; this module is the
internal entry point another layer composes.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...model.internal.dto.blueprint_dto import DataPartDTO


def data_to_document(data: DataPartDTO) -> dict[str, Any]:
    """Encode the table language part as its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.table.model.internal.dto import (
            DataPartDTO, data_to_document,
        )

        document = data_to_document(DataPartDTO((), (), (), ()))
        ```
    """
    from .._private.codec import data_to_document as encode

    return encode(data)


def data_from_document(value: Mapping[str, Any]) -> DataPartDTO:
    """Decode the table language part from its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.table.model.internal.dto import (
            data_from_document,
        )

        data = data_from_document({
            "structs": [], "relations": [], "projections": [], "sources": [],
        })
        ```
    """
    from .._private.codec import data_from_document as decode

    return decode(value)


__all__ = ["data_from_document", "data_to_document"]
