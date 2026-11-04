"""Projection and relation-value construction for the data language.

The planning lives in the package's private zone; each name here is a thin
delegation kept for the internal service path.
"""
from __future__ import annotations

from typing import Any


def projection_base(row_source: Any) -> type[Any]:
    """Return a dynamic base pinned to one row source."""
    from .._private.declarations import projection_base as base

    return base(row_source)


def projection_row_source(declaration: type[Any]) -> Any | None:
    """Return the pinned plan or the plan derived from an old-style projection."""
    from .._private.declarations import projection_row_source as row_source

    return row_source(declaration)


def relation_plan_dto(source: type[Any]) -> Any:
    """Return the scan plan for one named table or projection relation."""
    from ...model.internal.dto.blueprint_dto import RowScanDTO
    from .._private.rows import declaration_source_name

    return RowScanDTO(declaration_source_name(source))


__all__ = [
    "projection_base", "projection_row_source", "relation_plan_dto",
]
