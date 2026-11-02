"""Compilation IR for logical types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(frozen=True, slots=True)
class UnitTypeIR:
    name: Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]


@dataclass(frozen=True, slots=True)
class CustomTypeIR:
    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class StructTypeIR:
    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class ArrayTypeIR:
    item: "LogicalTypeIR"


@dataclass(frozen=True, slots=True)
class NullableTypeIR:
    value: "NonNullableLogicalTypeIR"


NonNullableLogicalTypeIR: TypeAlias = UnitTypeIR | CustomTypeIR | StructTypeIR | ArrayTypeIR
LogicalTypeIR: TypeAlias = NonNullableLogicalTypeIR | NullableTypeIR


__all__ = [
    "ArrayTypeIR", "CustomTypeIR", "LogicalTypeIR", "NonNullableLogicalTypeIR",
    "NullableTypeIR", "StructTypeIR", "UnitTypeIR",
]
