"""Compilation IR for logical types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(frozen=True, slots=True)
class UnitTypeIR:
    """A canonical unit type in the compilation IR.

    Example:
        ```python
        from kg_build_system.types.ir import UnitTypeIR

        UnitTypeIR("timestamp")
        ```
    """

    name: Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]


@dataclass(frozen=True, slots=True)
class CustomTypeIR:
    """An application-defined scalar identity in the compilation IR.

    Example:
        ```python
        from kg_build_system.types.ir import CustomTypeIR

        CustomTypeIR("example.types", "TenantId")
        ```
    """

    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class StructTypeIR:
    """A declared value-record identity in the compilation IR.

    Example:
        ```python
        from kg_build_system.types.ir import StructTypeIR

        StructTypeIR("example.types", "Address")
        ```
    """

    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class ArrayTypeIR:
    """An array type in the compilation IR.

    Example:
        ```python
        from kg_build_system.types.ir import ArrayTypeIR, UnitTypeIR

        ArrayTypeIR(UnitTypeIR("str"))
        ```
    """

    item: "LogicalTypeIR"


@dataclass(frozen=True, slots=True)
class NullableTypeIR:
    """A nullable wrapper in the compilation IR.

    Example:
        ```python
        from kg_build_system.types.ir import NullableTypeIR, UnitTypeIR

        NullableTypeIR(UnitTypeIR("str"))
        ```
    """

    value: "NonNullableLogicalTypeIR"


NonNullableLogicalTypeIR: TypeAlias = UnitTypeIR | CustomTypeIR | StructTypeIR | ArrayTypeIR
LogicalTypeIR: TypeAlias = NonNullableLogicalTypeIR | NullableTypeIR


__all__ = [
    "ArrayTypeIR", "CustomTypeIR", "LogicalTypeIR", "NonNullableLogicalTypeIR",
    "NullableTypeIR", "StructTypeIR", "UnitTypeIR",
]
