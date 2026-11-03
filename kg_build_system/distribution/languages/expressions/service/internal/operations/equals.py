"""The text equality operation."""
from __future__ import annotations

from ..._private.operations import nullable_bool_result, validate_text_operation
from ..._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


EQUALS = OperationSpec(
    name="equals",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
    ),
    result_type=nullable_bool_result,
    validate_arguments=validate_text_operation("equals"),
)


__all__ = ["EQUALS"]
