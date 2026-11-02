"""Logical type vocabulary shared by declarations and expressions."""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Final, Generic, Literal, TypeGuard, TypeVar


class CustomDataType:
    """Base for an application-defined scalar type."""


class Shape:
    """Base for a class-level row shape."""


class Struct(Shape):
    """A shape that is only a nested record, never a row source."""


T_co = TypeVar("T_co", covariant=True)


class Array(Generic[T_co]):
    """Author-facing marker for an ordered collection."""


class Nullable(Generic[T_co]):
    """Internal marker after ``T | None`` is normalized."""


Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
Uuid = uuid.UUID


def canonical_value_text(value: Date | Time | Timestamp | Uuid) -> str:
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"{type(value).__qualname__} has no canonical text form")


type UnitTypeName = Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]

CANONICAL_UNIT_NAMES: Final = frozenset({
    "bool", "int", "float", "str", "date", "time", "timestamp", "uuid",
})
TEXT_CANONICAL_UNIT_NAMES: Final[frozenset[UnitTypeName]] = frozenset({
    "date", "time", "timestamp", "uuid",
})


def is_canonical_unit_name(name: str) -> TypeGuard[UnitTypeName]:
    return name in CANONICAL_UNIT_NAMES


@dataclass(frozen=True, slots=True)
class UnitType:
    name: UnitTypeName

    def __post_init__(self) -> None:
        if not is_canonical_unit_name(self.name):
            raise ValueError(f"unknown unit logical type {self.name!r}")


@dataclass(frozen=True, slots=True)
class CustomType:
    module: str
    qualname: str

    def __post_init__(self) -> None:
        if not self.module or not self.qualname:
            raise ValueError("custom logical types require a module and qualified name")


@dataclass(frozen=True, slots=True)
class StructType:
    module: str
    qualname: str

    def __post_init__(self) -> None:
        if not self.module or not self.qualname:
            raise ValueError("struct logical types require a module and qualified name")


@dataclass(frozen=True, slots=True)
class ArrayType:
    item: "LogicalType"


@dataclass(frozen=True, slots=True)
class NullableType:
    value: "NonNullableLogicalType"

    def __post_init__(self) -> None:
        if isinstance(self.value, NullableType):
            raise ValueError("canonical nullable types may not be nested")


type NonNullableLogicalType = UnitType | CustomType | StructType | ArrayType
type LogicalType = NonNullableLogicalType | NullableType


BOOL = UnitType("bool")
INT = UnitType("int")
FLOAT = UnitType("float")
STR = UnitType("str")
DATE = UnitType("date")
TIME = UnitType("time")
TIMESTAMP = UnitType("timestamp")
UUID = UnitType("uuid")


__all__ = [
    "Array", "ArrayType", "BOOL", "CANONICAL_UNIT_NAMES", "CustomDataType",
    "CustomType", "DATE", "Date", "FLOAT", "INT", "LogicalType", "NonNullableLogicalType",
    "Nullable", "NullableType", "STR", "Shape", "Struct", "StructType",
    "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP", "Time", "Timestamp",
    "UUID", "UnitType", "UnitTypeName", "Uuid", "canonical_value_text",
    "is_canonical_unit_name",
]
