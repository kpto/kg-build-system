"""Authoring surface: Field descriptor and field() factory.

Maps authoring types (T | None) to ValuePlan specialisations:
  unit            → ValuePlan[T]
  nullable unit   → NullableValuePlan[T]
  array           → ArrayValuePlan[TItem]
  nullable array  → NullableValuePlan[Array[TItem]]
  struct          → StructValuePlan[S]
  nullable struct → NullableValuePlan[S]
"""
from typing import Any, overload

from model_concept import (
    Array,
    ArrayValuePlan,
    CustomDataType,
    Nullable,
    NullableDataType,
    NullableValuePlan,
    Struct,
    StructValuePlan,
    UnitType,
    ValuePlan,
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
    """Field access yields a ValuePlan (structural specialisation when needed)."""

    # --- units (UnitType, not per-scalar fan-out) ---
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[TUnit]", instance: Any, owner: type[Struct]
    ) -> ValuePlan[TUnit]: ...
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[TUnit | None]", instance: Any, owner: type[Struct]
    ) -> NullableValuePlan[TUnit]: ...

    # --- arrays ---
    @overload
    def __get__[TItem: NullableDataType](
        self: "Field[Array[TItem]]", instance: Any, owner: type[Struct]
    ) -> ArrayValuePlan[TItem]: ...
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[Array[TUnit | None]]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> ArrayValuePlan[Nullable[TUnit]]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct | None]]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> ArrayValuePlan[Nullable[TStruct]]: ...

    # --- nullable arrays ---
    @overload
    def __get__[TItem: NullableDataType](
        self: "Field[Array[TItem] | None]", instance: Any, owner: type[Struct]
    ) -> NullableValuePlan[Array[TItem]]: ...
    @overload
    def __get__[TUnit: UnitType](
        self: "Field[Array[TUnit | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> NullableValuePlan[Array[Nullable[TUnit]]]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type[Struct],
    ) -> NullableValuePlan[Array[Nullable[TStruct]]]: ...

    # --- structs ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[TStruct]", instance: Any, owner: type[Struct]
    ) -> StructValuePlan[TStruct]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[TStruct | None]", instance: Any, owner: type[Struct]
    ) -> NullableValuePlan[TStruct]: ...

    def __get__(self, instance: Any, owner: Any) -> ValuePlan[Any]: ...


def field[TType: AuthoringDataType]() -> Field[TType]: ...  # pyright: ignore[reportInvalidTypeVarUse]
