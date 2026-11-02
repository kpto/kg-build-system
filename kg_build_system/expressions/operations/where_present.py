"""The presence filter operation."""
from __future__ import annotations

from ...types.interfaces import non_nullable
from .spec import ArgumentSpec, OperationSpec, RowEffectSpec


WHERE_PRESENT = OperationSpec(
    name="where_present",
    arity=1,
    arguments=(ArgumentSpec(description="value"),),
    result_type=lambda types, parameters: non_nullable(types[0]),
    row_effect=RowEffectSpec("filter"),
)


__all__ = ["WHERE_PRESENT"]
