"""DTOs for the canonical logical types.

A DTO is the serialisable form of a logical type. It carries the same facts as
the canonical model, uses the ``DTO`` suffix and is owned by the kernel's
internal type interface.

Example:
    ```python
    from kg_build_system.kernel.model.internal.types import UnitTypeDTO

    UnitTypeDTO("timestamp")
    ```
"""
from __future__ import annotations

from dataclasses import dataclass

from ...public.types.model import UnitTypeName


@dataclass(frozen=True, slots=True)
class UnitTypeDTO:
    """A canonical unit type in serialisable form.

    Example:
        ```python
        from kg_build_system.kernel.model.internal.types import UnitTypeDTO

        UnitTypeDTO("timestamp")
        ```
    """

    name: UnitTypeName


@dataclass(frozen=True, slots=True)
class CustomTypeDTO:
    """An application-defined scalar identity in serialisable form.

    Example:
        ```python
        from kg_build_system.kernel.model.internal.types import CustomTypeDTO

        CustomTypeDTO("example.types", "TenantId")
        ```
    """

    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class StructTypeDTO:
    """A declared value-record identity in serialisable form.

    Example:
        ```python
        from kg_build_system.kernel.model.internal.types import StructTypeDTO

        StructTypeDTO("example.types", "Address")
        ```
    """

    module: str
    qualname: str


@dataclass(frozen=True, slots=True)
class ArrayTypeDTO:
    """An array type in serialisable form.

    Example:
        ```python
        from kg_build_system.kernel.model.internal.types import ArrayTypeDTO, UnitTypeDTO

        ArrayTypeDTO(UnitTypeDTO("str"))
        ```
    """

    item: "LogicalTypeDTO"


@dataclass(frozen=True, slots=True)
class NullableTypeDTO:
    """A nullable wrapper in serialisable form.

    Example:
        ```python
        from kg_build_system.kernel.model.internal.types import NullableTypeDTO, UnitTypeDTO

        NullableTypeDTO(UnitTypeDTO("str"))
        ```
    """

    value: "NonNullableLogicalTypeDTO"


type NonNullableLogicalTypeDTO = (
    UnitTypeDTO | CustomTypeDTO | StructTypeDTO | ArrayTypeDTO
)
type LogicalTypeDTO = NonNullableLogicalTypeDTO | NullableTypeDTO


__all__ = [
    "ArrayTypeDTO", "CustomTypeDTO", "LogicalTypeDTO",
    "NonNullableLogicalTypeDTO", "NullableTypeDTO", "StructTypeDTO",
    "UnitTypeDTO",
]
