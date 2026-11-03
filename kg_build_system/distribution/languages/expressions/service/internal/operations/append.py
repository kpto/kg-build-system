"""The text append operation.

It has the same contract as ``concat`` and exists as a named operation for
callers that prefer the append spelling; the authoring method uses ``concat`` so
the established engine emission keeps one implementation.
"""
from __future__ import annotations

from ..._private.operations import nullable_str_result, validate_text_operation
from ..._private.predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


APPEND = OperationSpec(
    name="append",
    arity=(2, None),
    arguments=(ArgumentSpec(accepts=is_unit("str"), description="str value"),),
    repeat_last_argument=True,
    result_type=nullable_str_result,
    validate_arguments=validate_text_operation("append"),
)


__all__ = ["APPEND"]
