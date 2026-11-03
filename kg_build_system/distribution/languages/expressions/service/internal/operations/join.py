"""The array-to-text join operation."""
from __future__ import annotations

from kg_build_system.kernel.model.public.types import STR
from ..._private.operations import join_result
from ..._private.predicates import is_array_of, is_exact, is_non_null_unit
from .spec import ArgumentSpec, OperationSpec


JOIN = OperationSpec(
    name="join",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array_of(is_non_null_unit("str")), description="array of non-null strings"),
        ArgumentSpec(expected=STR, accepts=is_exact(STR), description="separator"),
    ),
    result_type=join_result,
)


__all__ = ["JOIN"]
