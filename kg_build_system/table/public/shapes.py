"""Author-facing row-shape member values.

A ``ShapeField`` names one member of a row: its Python attribute, its external
name and its logical type. Row-source plan helpers return these values and
accept them when a shape is derived from plan IR.

Example:
    ```python
    from kg_build_system import ShapeField, make_row_shape

    shape = make_row_shape(
        "sites",
        (ShapeField("site_id", "site_id", SiteTable.site_id.logical_type),),
    )
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ShapeField:
    """One member of a row shape, in both attribute and external form."""

    attribute: str
    name: str
    logical_type: Any


__all__ = ["ShapeField"]
