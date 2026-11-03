"""The canonical logical type model.

A logical type is a canonical unit, an application-defined scalar, a declared
struct identity, an array, or a nullable wrapper. The model is frozen data: it
carries no owner, service or behaviour beyond its own invariants.

Example:
    ```python
    from kg_build_system.kernel.public.types import ArrayType, INT, NullableType

    ArrayType(INT)
    NullableType(INT)
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeGuard


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
        from kg_build_system.kernel.public.types import is_canonical_unit_name

        assert is_canonical_unit_name("timestamp")
        ```
    """
    return name in CANONICAL_UNIT_NAMES


@dataclass(frozen=True, slots=True)
class UnitType:
    """A canonical unit logical type such as ``int`` or ``timestamp``.

    Example:
        ```python
        from kg_build_system.kernel.public.types import UnitType

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
        from kg_build_system.kernel.public.types import CustomType

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
        from kg_build_system.kernel.public.types import StructType

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
        from kg_build_system.kernel.public.types import ArrayType, STR

        ArrayType(STR)
        ```
    """

    item: "LogicalType"


@dataclass(frozen=True, slots=True)
class NullableType:
    """A canonical nullable wrapper around one non-nullable logical type.

    Example:
        ```python
        from kg_build_system.kernel.public.types import NullableType, STR

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
    "ArrayType", "BOOL", "CANONICAL_UNIT_NAMES", "CustomType", "DATE",
    "FLOAT", "INT", "LogicalType", "NonNullableLogicalType", "NullableType",
    "STR", "StructType", "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP",
    "UUID", "UnitType", "UnitTypeName", "is_canonical_unit_name",
]
