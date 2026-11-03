"""The text-after-separator operation."""
from __future__ import annotations

from ..._private.operations import (
    nullable_str_result, positive_integer, validate_text_operation,
)
from ..._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec, ParameterSpec


AFTER_SEPARATOR = OperationSpec(
    name="after_separator",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="separator"),
    ),
    parameters=(
        ParameterSpec("occurrence", default=1, accepts=positive_integer),
        ParameterSpec("include_separator", default=False, accepts=lambda value: isinstance(value, bool)),
    ),
    result_type=nullable_str_result,
    validate_arguments=validate_text_operation("after_separator"),
)


__all__ = ["AFTER_SEPARATOR"]
