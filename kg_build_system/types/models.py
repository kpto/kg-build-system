"""Canonical logical types shared by declarations, expressions, and IR."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


class CustomDataType:
    """Base for portable, application-defined scalar types."""


class Struct:
    """Base for portable nested-record declarations."""


T_co = TypeVar("T_co", covariant=True)


class Array(Generic[T_co]):
    """Author-facing marker for an ordered collection of logical values."""


class Nullable(Generic[T_co]):
    """Internal marker used after author-facing ``T | None`` is normalized."""


@dataclass(frozen=True, slots=True)
class UnitType:
    """A built-in scalar logical type."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in {"bool", "int", "float", "str"}:
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


__all__ = [
    "Array", "ArrayType", "BOOL", "CustomDataType", "CustomType", "FLOAT", "INT",
    "LogicalType", "NonNullableLogicalType", "Nullable", "NullableType", "STR", "Struct",
    "StructType", "UnitType",
]
