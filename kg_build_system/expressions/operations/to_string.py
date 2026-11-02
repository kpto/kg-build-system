"""The canonical scalar-to-text operation."""
from __future__ import annotations

from ...types.interfaces import STR, NullableType, UnitType, non_nullable
from .spec import ArgumentSpec, OperationSpec


def _accepts(logical_type) -> bool:
    return isinstance(non_nullable(logical_type), UnitType)


def _result(types, parameters):
    return NullableType(STR) if isinstance(types[0], NullableType) else STR


TO_STRING = OperationSpec(
    name="to_string",
    arity=1,
    arguments=(ArgumentSpec(accepts=_accepts, description="canonical scalar"),),
    result_type=_result,
)


__all__ = ["TO_STRING"]
