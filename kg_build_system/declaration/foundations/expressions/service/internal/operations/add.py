"""The numeric addition operation."""
from __future__ import annotations

from ..._private.operations import validate_numeric_operation
from ..._private.predicates import is_numeric
from .spec import ArgumentSpec, OperationSpec


ADD = OperationSpec(
    name="add",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_numeric, description="numeric value"),
        ArgumentSpec(accepts=is_numeric, description="numeric value"),
    ),
    result_type=lambda types, parameters: types[0],
    validate_arguments=validate_numeric_operation("add"),
)


__all__ = ["ADD"]
