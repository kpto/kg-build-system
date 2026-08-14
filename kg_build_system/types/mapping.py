"""Mappings from logical-type domain models to compilation DTOs."""
from __future__ import annotations

from typing import Any, cast

from . import dto
from . import models


def type_to_dto(value: models.LogicalType) -> dto.LogicalTypeDTO:
    if isinstance(value, models.UnitType):
        return dto.UnitTypeDTO(cast(Any, value.name))
    if isinstance(value, models.CustomType):
        return dto.CustomTypeDTO(value.module, value.qualname)
    if isinstance(value, models.StructType):
        return dto.StructTypeDTO(value.module, value.qualname)
    if isinstance(value, models.ArrayType):
        return dto.ArrayTypeDTO(type_to_dto(value.item))
    if isinstance(value, models.NullableType):
        inner = type_to_dto(value.value)
        if isinstance(inner, dto.NullableTypeDTO):
            raise ValueError("nullable type DTOs may not be nested")
        return dto.NullableTypeDTO(inner)
    raise TypeError(f"unsupported logical type domain model {value!r}")


__all__ = ["type_to_dto"]
