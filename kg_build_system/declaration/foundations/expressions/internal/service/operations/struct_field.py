"""The struct member read operation."""
from __future__ import annotations

from ...._private.predicates import is_struct
from .spec import ArgumentSpec, OperationSpec, ParameterSpec


STRUCT_FIELD = OperationSpec(
    name="struct_field",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_struct, description="struct value"),),
    parameters=(ParameterSpec("name", accepts=lambda value: isinstance(value, str) and bool(value)),),
)


__all__ = ["STRUCT_FIELD"]
