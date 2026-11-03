"""The row-producing array expansion operation."""
from __future__ import annotations

from ..._private.operations import expand_result, expand_scope_of
from ..._private.predicates import is_array
from .spec import ArgumentSpec, OperationSpec, RowEffectSpec


EXPAND = OperationSpec(
    name="expand",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_array, description="array value"),),
    result_type=expand_result,
    row_effect=RowEffectSpec("expand", scope=expand_scope_of),
)


__all__ = ["EXPAND"]
