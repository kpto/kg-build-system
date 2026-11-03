"""The canonical scalar-to-text operation."""
from __future__ import annotations

from ..._private.operations import nullable_str_result
from ..._private.predicates import is_scalar_unit
from .spec import ArgumentSpec, OperationSpec


TO_STRING = OperationSpec(
    name="to_string",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_scalar_unit, description="canonical scalar"),),
    result_type=nullable_str_result,
)


__all__ = ["TO_STRING"]
