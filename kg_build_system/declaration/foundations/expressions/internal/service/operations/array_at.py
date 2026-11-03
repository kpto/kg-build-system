"""The 0-based array index operation."""
from __future__ import annotations

from .......kernel.internal.types import INT
from ...._private.operations import array_at_result
from ...._private.predicates import is_array, is_exact
from .spec import ArgumentSpec, OperationSpec


ARRAY_AT = OperationSpec(
    name="array_at",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array, description="array value"),
        ArgumentSpec(expected=INT, accepts=is_exact(INT), description="integer index"),
    ),
    result_type=array_at_result,
)


__all__ = ["ARRAY_AT"]
