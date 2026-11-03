"""The authoring markers and representative aliases for logical types.

A graph author writes these names directly: ``Array[T]``, ``Nullable[T]``, the
``CustomDataType`` and ``Struct`` base classes, and the representative aliases
``Date``, ``Time``, ``Timestamp`` and ``Uuid``.

Example:
    ```python
    from kg_build_system.kernel.model.public.types import Array, INT, Nullable

    Array[INT]
    Nullable[INT]
    ```
"""
from __future__ import annotations

import datetime
import uuid
from typing import Generic, TypeVar


class CustomDataType:
    """Base for an application-defined scalar type.

    Example:
        ```python
        from dataclasses import dataclass
        from kg_build_system.kernel.model.public.types import CustomDataType

        @dataclass(frozen=True)
        class TenantId(CustomDataType):
            value: str
        ```
    """


class Shape:
    """Base for a class-level row shape.

    Example:
        ```python
        from kg_build_system.kernel.model.public.types import Shape

        class Readings(Shape):
            pass
        ```
    """


class Struct(Shape):
    """A shape that is only a nested record, never a row source.

    Example:
        ```python
        from kg_build_system.kernel.model.public.types import Struct

        class Address(Struct):
            pass
        ```
    """


T_co = TypeVar("T_co", covariant=True)


class Array(Generic[T_co]):
    """Author-facing marker for an ordered collection.

    Example:
        ```python
        from kg_build_system.kernel.model.public.types import Array

        Array[str]
        ```
    """


class Nullable(Generic[T_co]):
    """Explicit nullable marker; ``T | None`` normalizes to the same value.

    Example:
        ```python
        from kg_build_system.kernel.model.public.types import Nullable

        Nullable[str]
        ```
    """


Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
Uuid = uuid.UUID


__all__ = [
    "Array", "CustomDataType", "Date", "Nullable", "Shape", "Struct", "Time",
    "Timestamp", "Uuid",
]
