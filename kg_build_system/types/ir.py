"""Compatibility shim for :mod:`kg_build_system.types.internal.ir`."""
from __future__ import annotations

from .internal.ir import (
    ArrayTypeIR, CustomTypeIR, LogicalTypeIR, NonNullableLogicalTypeIR,
    NullableTypeIR, StructTypeIR, UnitTypeIR,
)

__all__ = [
    "ArrayTypeIR", "CustomTypeIR", "LogicalTypeIR", "NonNullableLogicalTypeIR",
    "NullableTypeIR", "StructTypeIR", "UnitTypeIR",
]
