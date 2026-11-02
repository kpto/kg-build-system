"""The value-scoped predicate filter operation."""
from __future__ import annotations

from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec, RowEffectSpec


WHERE_IF = OperationSpec(
    name="where_if",
    arity=2,
    arguments=(
        ArgumentSpec(description="value"),
        ArgumentSpec(accepts=is_unit("bool"), description="Boolean predicate"),
    ),
    result_type=lambda types, parameters: types[0],
    row_effect=RowEffectSpec("filter", predicate_index=1),
)


__all__ = ["WHERE_IF"]
