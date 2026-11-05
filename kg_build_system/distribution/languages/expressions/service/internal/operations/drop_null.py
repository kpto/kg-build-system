"""The drop-null row filter operation."""
from __future__ import annotations

from kg_build_system.kernel.service.internal.types import non_nullable
from .spec import ArgumentSpec, OperationSpec, RowEffectSpec


DROP_NULL = OperationSpec(
    name="drop_null",
    arity=1,
    arguments=(ArgumentSpec(description="value"),),
    result_type=lambda types, parameters: non_nullable(types[0]),
    row_effect=RowEffectSpec("filter"),
)


__all__ = ["DROP_NULL"]
