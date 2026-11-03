"""The text concatenation operation."""
from __future__ import annotations

from ...._private.operations import nullable_str_result, validate_text_operation
from ...._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


CONCAT = OperationSpec(
    name="concat",
    arity=(2, None),
    arguments=(ArgumentSpec(accepts=is_unit("str"), description="str value"),),
    repeat_last_argument=True,
    result_type=nullable_str_result,
    validate_arguments=validate_text_operation("concat"),
)


__all__ = ["CONCAT"]
