"""The ascending array sort operation."""
from __future__ import annotations

from ._predicates import is_array
from .spec import ArgumentSpec, OperationSpec


SORT = OperationSpec(
    name="sort",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_array, description="array value"),),
    result_type=lambda types, parameters: types[0],
)


__all__ = ["SORT"]
