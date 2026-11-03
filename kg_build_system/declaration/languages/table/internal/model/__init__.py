# pyright: reportUnsupportedDunderAll=false
"""Internal table models: declaration specs, field specs and row algebra."""
from __future__ import annotations

from typing import Any

from .declarations import DeclarationSpec
from .fields import FieldSpec

_LAZY = {
    "as_row_source": "as_row_source",
    "declaration_source_name": "declaration_source_name",
    "derive_distinct": "derive_distinct",
    "derive_group_by": "derive_group_by",
    "derive_join": "derive_join",
    "derive_order_by": "derive_order_by",
    "derive_row_source": "derive_row_source",
    "derive_union": "derive_union",
    "derive_where": "derive_where",
    "plan_expressions": "plan_expressions",
    "plan_fields": "plan_fields",
    "plan_inputs": "plan_inputs",
    "plan_scan_sources": "plan_scan_sources",
    "plan_shape_source_name": "plan_shape_source_name",
    "retarget_expression_dto": "retarget_expression_dto",
    "row_source_key": "row_source_key",
    "row_source_plan_dto": "row_source_plan_dto",
}


def __getattr__(name: str) -> Any:
    try:
        attribute = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from . import rows

    value = getattr(rows, attribute)
    globals()[name] = value
    return value


__all__ = ["DeclarationSpec", "FieldSpec", *_LAZY]
