"""Authoring surface: Field descriptor and field() factory.

Maps authoring types (T | None) to ValueSelection specialisations:
  unit            → ValueSelection[T]
  nullable unit   → NullableSelection[T]
  array           → ArraySelection[TItem]
  nullable array  → NullableSelection[Array[TItem]]
  struct          → StructSelection[S]
  nullable struct → NullableSelection[S]
"""
from typing import Any, overload

from model_concept import (
    Array,
    ArraySelection,
    CustomDataType,
    Nullable,
    NullableDataType,
    NullableSelection,
    Struct,
    StructSelection,
    UnitType,
    ValueSelection,
)

# Authoring-only: nullability is T | None. Core types use Nullable[T].
type AuthoringDataType = (
    bool
    | int
    | float
    | str
    | CustomDataType
    | Struct
    | Array[NullableDataType]
    | None
)


class Field[T: AuthoringDataType]:
    """Field access yields a selection specialized by logical shape."""

    # --- units (UnitType, not per-scalar fan-out) ---
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[TUnit]", instance: Any, owner: type[Struct]
    ) -> ValueSelection[TUnit]: ...
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[TUnit | None]", instance: Any, owner: type[Struct]
    ) -> NullableSelection[TUnit]: ...

    # --- arrays ---
    @overload
    def __get__[TItem: NullableDataType](
        self: "Field[Array[TItem]]", instance: Any, owner: type[Struct]
    ) -> ArraySelection[TItem]: ...
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[Array[TUnit | None]]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> ArraySelection[Nullable[TUnit]]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct | None]]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> ArraySelection[Nullable[TStruct]]: ...

    # --- nullable arrays ---
    @overload
    def __get__[TItem: NullableDataType](
        self: "Field[Array[TItem] | None]", instance: Any, owner: type[Struct]
    ) -> NullableSelection[Array[TItem]]: ...
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[Array[TUnit | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> NullableSelection[Array[Nullable[TUnit]]]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> NullableSelection[Array[Nullable[TStruct]]]: ...

    # --- structs ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[TStruct]", instance: Any, owner: type[Struct]
    ) -> StructSelection[TStruct]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[TStruct | None]", instance: Any, owner: type[Struct]
    ) -> NullableSelection[TStruct]: ...

    def __get__(self, instance: Any, owner: Any) -> ValueSelection[Any]: ...


def field[TType: AuthoringDataType]() -> Field[TType]: ...  # pyright: ignore[reportInvalidTypeVarUse]
