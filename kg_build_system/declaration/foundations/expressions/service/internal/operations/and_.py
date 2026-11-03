"""The Boolean conjunction operation."""
from __future__ import annotations

from ..._private.operations import nullable_bool_result
from ..._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


AND = OperationSpec(
    name="and",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_unit("bool"), description="Boolean value"),
        ArgumentSpec(accepts=is_unit("bool"), description="Boolean value"),
    ),
    result_type=nullable_bool_result,
)


__all__ = ["AND"]
