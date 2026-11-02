"""The logical type vocabulary an author writes.

This module holds the authoring markers, representative aliases and canonical
unit constants that a graph author uses directly.

Example:
    ```python
    from kg_build_system.types import Array, INT, Nullable

    Array[INT]
    Nullable[str]
    ```
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Final, Generic, Literal, TypeGuard, TypeVar


class CustomDataType:
    """Base for an application-defined scalar type.

    Example:
        ```python
        from dataclasses import dataclass
        from kg_build_system.types import CustomDataType

        @dataclass(frozen=True)
        class TenantId(CustomDataType):
            value: str
        ```
    """


class Shape:
    """Base for a class-level row shape.

    Example:
        ```python
        from kg_build_system.types import Shape

        class Readings(Shape):
            pass
        ```
    """


class Struct(Shape):
    """A shape that is only a nested record, never a row source.

    Example:
        ```python
        from kg_build_system.types import Struct

        class Address(Struct):
            pass
        ```
    """


T_co = TypeVar("T_co", covariant=True)


class Array(Generic[T_co]):
    """Author-facing marker for an ordered collection.

    Example:
        ```python
        from kg_build_system.types import Array

        Array[str]
        ```
    """


class Nullable(Generic[T_co]):
    """Explicit nullable marker; ``T | None`` normalizes to the same value.

    Example:
        ```python
        from kg_build_system.types import Nullable

        Nullable[str]
        ```
    """


Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
Uuid = uuid.UUID

type UnitTypeName = Literal[
    "bool", "int", "float", "str", "date", "time", "timestamp", "uuid",
]

CANONICAL_UNIT_NAMES: Final = frozenset({
    "bool", "int", "float", "str", "date", "time", "timestamp", "uuid",
})
TEXT_CANONICAL_UNIT_NAMES: Final[frozenset[UnitTypeName]] = frozenset({
    "date", "time", "timestamp", "uuid",
})


def is_canonical_unit_name(name: str) -> TypeGuard[UnitTypeName]:
    """Return whether ``name`` is one of the canonical unit type names.

    Example:
        ```python
        from kg_build_system.types import is_canonical_unit_name

        assert is_canonical_unit_name("timestamp")
        ```
    """
    return name in CANONICAL_UNIT_NAMES


@dataclass(frozen=True, slots=True)
class UnitType:
    """A canonical unit logical type such as ``int`` or ``timestamp``.

    Example:
        ```python
        from kg_build_system.types import UnitType

        UnitType("timestamp")
        ```
    """

    name: UnitTypeName

    def __post_init__(self) -> None:
        if not is_canonical_unit_name(self.name):
            raise ValueError(f"unknown unit logical type {self.name!r}")


@dataclass(frozen=True, slots=True)
class CustomType:
    """An application-defined scalar identified by module and qualified name.

    Example:
        ```python
        from kg_build_system.types import CustomType

        CustomType("example.types", "TenantId")
        ```
    """

    module: str
    qualname: str

    def __post_init__(self) -> None:
        if not self.module or not self.qualname:
            raise ValueError("custom logical types require a module and qualified name")


@dataclass(frozen=True, slots=True)
class StructType:
    """A declared value record identified by module and qualified name.

    Example:
        ```python
        from kg_build_system.types import StructType

        StructType("example.types", "Address")
        ```
    """

    module: str
    qualname: str

    def __post_init__(self) -> None:
        if not self.module or not self.qualname:
            raise ValueError("struct logical types require a module and qualified name")


@dataclass(frozen=True, slots=True)
class ArrayType:
    """A logical array type with one item type.

    Example:
        ```python
        from kg_build_system.types import ArrayType, STR

        ArrayType(STR)
        ```
    """

    item: "LogicalType"


@dataclass(frozen=True, slots=True)
class NullableType:
    """A canonical nullable wrapper around one non-nullable logical type.

    Example:
        ```python
        from kg_build_system.types import NullableType, STR

        NullableType(STR)
        ```
    """

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
    "UUID", "UnitType", "UnitTypeName", "Uuid",
]
