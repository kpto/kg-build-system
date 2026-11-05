"""The value-scoped predicate filter operation."""
from __future__ import annotations

from ..._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec, RowEffectSpec


DROP_IF = OperationSpec(
    name="drop_if",
    arity=2,
    arguments=(
        ArgumentSpec(description="value"),
        ArgumentSpec(accepts=is_unit("bool"), description="Boolean predicate"),
    ),
    result_type=lambda types, parameters: types[0],
    row_effect=RowEffectSpec("filter", predicate_index=1),
)


__all__ = ["DROP_IF"]
