"""Private import surface for the row-source algebra.

The algebra itself is owned by :mod:`.._private.model.rows`; this module exists
so class-creation mechanics can import it without reaching into the internal
package's modules directly.
"""
from __future__ import annotations

from .model.rows import (
    as_row_source, declaration_source_name, derive_distinct, derive_group_by,
    derive_join, derive_order_by, derive_row_source, derive_union, derive_where,
    plan_expressions, plan_fields, plan_inputs, plan_scan_sources,
    plan_shape_source_name, retarget_expression_dto, row_source_key,
    row_source_plan_dto,
)

__all__ = [
    "as_row_source", "declaration_source_name", "derive_distinct",
    "derive_group_by", "derive_join", "derive_order_by", "derive_row_source",
    "derive_union", "derive_where", "plan_expressions", "plan_fields",
    "plan_inputs", "plan_scan_sources", "plan_shape_source_name",
    "retarget_expression_dto", "row_source_key", "row_source_plan_dto",
]
