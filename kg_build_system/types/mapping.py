"""Mappings from logical-type domain models to compilation IRs."""
from __future__ import annotations

from . import ir
from . import models


def type_to_ir(value: models.LogicalType) -> ir.LogicalTypeIR:
    if isinstance(value, models.UnitType):
        return ir.UnitTypeIR(value.name)
    if isinstance(value, models.CustomType):
        return ir.CustomTypeIR(value.module, value.qualname)
    if isinstance(value, models.StructType):
        return ir.StructTypeIR(value.module, value.qualname)
    if isinstance(value, models.ArrayType):
        return ir.ArrayTypeIR(type_to_ir(value.item))
    if isinstance(value, models.NullableType):
        inner = type_to_ir(value.value)
        if isinstance(inner, ir.NullableTypeIR):
            raise ValueError("nullable type IRs may not be nested")
        return ir.NullableTypeIR(inner)
    raise TypeError(f"unsupported logical type domain model {value!r}")


__all__ = ["type_to_ir"]
