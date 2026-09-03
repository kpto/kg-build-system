"""Canonical logical types shared by declarations, expressions, and IR."""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Final, Generic, Literal, TypeGuard, TypeVar


class CustomDataType:
    """Base for portable, application-defined scalar types."""


class Struct:
    """Base for portable nested-record declarations."""


T_co = TypeVar("T_co", covariant=True)


class Array(Generic[T_co]):
    """Author-facing marker for an ordered collection of logical values."""


class Nullable(Generic[T_co]):
    """Internal marker used after author-facing ``T | None`` is normalized."""


# Representative types: the stdlib classes an author writes in an annotation for
# one canonical unit type. The capitalised spelling is what marks them as
# representatives, and each aliases the value class of the unit of the same
# lowercase canonical name, so both spellings are one and the same class.
Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
Uuid = uuid.UUID


type UnitTypeName = Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]

#: The canonical unit vocabulary; every gate on a unit name reads this set.
CANONICAL_UNIT_NAMES: Final = frozenset({
    "bool", "int", "float", "str", "date", "time", "timestamp", "uuid",
})


def is_canonical_unit_name(name: str) -> TypeGuard[UnitTypeName]:
    """Whether ``name`` is one of the canonical unit type names."""
    return name in CANONICAL_UNIT_NAMES


@dataclass(frozen=True, slots=True)
class UnitType:
    """A built-in scalar logical type."""

    name: UnitTypeName

    def __post_init__(self) -> None:
        if not is_canonical_unit_name(self.name):
            raise ValueError(f"unknown unit logical type {self.name!r}")


@dataclass(frozen=True, slots=True)
class CustomType:
    """A custom scalar identified independently of its Python class object."""

    module: str
    qualname: str

    def __post_init__(self) -> None:
        if not self.module or not self.qualname:
            raise ValueError("custom logical types require a module and qualified name")


@dataclass(frozen=True, slots=True)
class StructType:
    """A nested-record type identified by its declaration."""

    module: str
    qualname: str

    def __post_init__(self) -> None:
        if not self.module or not self.qualname:
            raise ValueError("struct logical types require a module and qualified name")


@dataclass(frozen=True, slots=True)
class ArrayType:
    item: LogicalType


@dataclass(frozen=True, slots=True)
class NullableType:
    value: NonNullableLogicalType

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
    "Array", "ArrayType", "BOOL", "CANONICAL_UNIT_NAMES", "CustomDataType", "CustomType",
    "DATE", "Date", "FLOAT", "INT", "LogicalType", "NonNullableLogicalType", "Nullable",
    "NullableType", "STR", "Struct", "StructType", "TIME", "TIMESTAMP", "Time", "Timestamp",
    "UUID", "UnitType", "UnitTypeName", "Uuid", "is_canonical_unit_name",
]
