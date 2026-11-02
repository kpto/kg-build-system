"""Domain logical type to compilation IR."""
from __future__ import annotations

from ..internal.ir import (
    ArrayTypeIR, CustomTypeIR, LogicalTypeIR, NullableTypeIR, StructTypeIR,
    UnitTypeIR,
)
from ..public.models import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
)


def type_to_ir(value: LogicalType) -> LogicalTypeIR:
    if isinstance(value, UnitType):
        return UnitTypeIR(value.name)
    if isinstance(value, CustomType):
        return CustomTypeIR(value.module, value.qualname)
    if isinstance(value, StructType):
        return StructTypeIR(value.module, value.qualname)
    if isinstance(value, ArrayType):
        return ArrayTypeIR(type_to_ir(value.item))
    if isinstance(value, NullableType):
        return NullableTypeIR(type_to_ir(value.value))  # type: ignore[arg-type]
    raise TypeError(f"unsupported logical type {value!r}")


__all__ = ["type_to_ir"]
