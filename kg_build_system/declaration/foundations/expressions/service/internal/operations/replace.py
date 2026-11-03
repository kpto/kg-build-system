"""The text replacement operation."""
from __future__ import annotations

from ..._private.operations import nullable_str_result, validate_text_operation
from ..._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


REPLACE = OperationSpec(
    name="replace",
    arity=3,
    arguments=(
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
    ),
    result_type=nullable_str_result,
    validate_arguments=validate_text_operation("replace"),
)


__all__ = ["REPLACE"]
