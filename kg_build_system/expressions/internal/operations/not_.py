"""The Boolean negation operation."""
from __future__ import annotations

from ....types.internal import BOOL, NullableType, non_nullable
from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    return NullableType(BOOL) if isinstance(types[0], NullableType) else BOOL


NOT = OperationSpec(
    name="not",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_unit("bool"), description="Boolean value"),),
    result_type=_result,
)


__all__ = ["NOT"]
