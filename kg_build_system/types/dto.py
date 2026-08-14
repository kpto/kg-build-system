"""Compilation-only transfer objects for normalized logical types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(frozen=True, slots=True)
class UnitTypeDTO:
    name: Literal["bool", "int", "float", "str"]


@dataclass(frozen=True, slots=True)
class CustomTypeDTO:
    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class StructTypeDTO:
    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class ArrayTypeDTO:
    item: "LogicalTypeDTO"


@dataclass(frozen=True, slots=True)
class NullableTypeDTO:
    value: "NonNullableLogicalTypeDTO"


NonNullableLogicalTypeDTO: TypeAlias = UnitTypeDTO | CustomTypeDTO | StructTypeDTO | ArrayTypeDTO
LogicalTypeDTO: TypeAlias = NonNullableLogicalTypeDTO | NullableTypeDTO


__all__ = [
    "ArrayTypeDTO", "CustomTypeDTO", "LogicalTypeDTO",
    "NonNullableLogicalTypeDTO", "NullableTypeDTO", "StructTypeDTO",
    "UnitTypeDTO",
]
