"""The array distinct operation."""
from __future__ import annotations

from ...._private.predicates import is_array
from .spec import ArgumentSpec, OperationSpec


DISTINCT = OperationSpec(
    name="distinct",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_array, description="array value"),),
    result_type=lambda types, parameters: types[0],
)


__all__ = ["DISTINCT"]
