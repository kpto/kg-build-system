"""Authoring surface: Field descriptor and field() factory.

Maps authoring types (T | None) to internal expression types (Nullable[T]).
"""
from typing import Any, overload

from model_concept import (
    Array,
    ArrayNullableValueExpression,
    ArrayValueExpression,
    BoolValueExpression,
    CustomDataType,
    CustomDataTypeValueExpression,
    FloatValueExpression,
    IntValueExpression,
    Nullable,
    NullableDataType,
    NullableValueExpression,
    PickedField,
    StrValueExpression,
    Struct,
    StructNullableValueExpression,
    StructValueExpression,
    Table,
    ValueExpression,
)

# Authoring-only: nullability is T | None. Core expressions keep Nullable[T].
# Array[T | None] is not a valid core Array[...] (item bound is NullableDataType);
# those overload lines are suppressed so Field can still expose the authoring form.
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
    # --- Table owner: non-null units ---
    @overload
    def __get__(
        self: "Field[bool]", instance: Any, owner: type["Table"]
    ) -> BoolValueExpression: ...
    @overload
    def __get__(
        self: "Field[int]", instance: Any, owner: type["Table"]
    ) -> IntValueExpression: ...
    @overload
    def __get__(
        self: "Field[float]", instance: Any, owner: type["Table"]
    ) -> FloatValueExpression: ...
    @overload
    def __get__(
        self: "Field[str]", instance: Any, owner: type["Table"]
    ) -> StrValueExpression: ...
    @overload
    def __get__[TType: CustomDataType](
        self: "Field[TType]", instance: Any, owner: type["Table"]
    ) -> CustomDataTypeValueExpression[TType]: ...

    # --- Table owner: nullable units ---
    @overload
    def __get__(
        self: "Field[bool | None]", instance: Any, owner: type["Table"]
    ) -> NullableValueExpression[bool, BoolValueExpression]: ...
    @overload
    def __get__(
        self: "Field[int | None]", instance: Any, owner: type["Table"]
    ) -> NullableValueExpression[int, IntValueExpression]: ...
    @overload
    def __get__(
        self: "Field[float | None]", instance: Any, owner: type["Table"]
    ) -> NullableValueExpression[float, FloatValueExpression]: ...
    @overload
    def __get__(
        self: "Field[str | None]", instance: Any, owner: type["Table"]
    ) -> NullableValueExpression[str, StrValueExpression]: ...
    @overload
    def __get__[TType: CustomDataType](
        self: "Field[TType | None]", instance: Any, owner: type["Table"]
    ) -> NullableValueExpression[TType, CustomDataTypeValueExpression[TType]]: ...

    # --- Table owner: arrays (non-null array) ---
    @overload
    def __get__(
        self: "Field[Array[bool]]", instance: Any, owner: type["Table"]
    ) -> ArrayValueExpression[bool, BoolValueExpression]: ...
    @overload
    def __get__(
        self: "Field[Array[int]]", instance: Any, owner: type["Table"]
    ) -> ArrayValueExpression[int, IntValueExpression]: ...
    @overload
    def __get__(
        self: "Field[Array[float]]", instance: Any, owner: type["Table"]
    ) -> ArrayValueExpression[float, FloatValueExpression]: ...
    @overload
    def __get__(
        self: "Field[Array[str]]", instance: Any, owner: type["Table"]
    ) -> ArrayValueExpression[str, StrValueExpression]: ...
    @overload
    def __get__(
        self: "Field[Array[bool | None]]", instance: Any, owner: type["Table"]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> ArrayValueExpression[
        Nullable[bool], NullableValueExpression[bool, BoolValueExpression]
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[int | None]]", instance: Any, owner: type["Table"]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> ArrayValueExpression[
        Nullable[int], NullableValueExpression[int, IntValueExpression]
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[float | None]]", instance: Any, owner: type["Table"]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> ArrayValueExpression[
        Nullable[float], NullableValueExpression[float, FloatValueExpression]
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[str | None]]", instance: Any, owner: type["Table"]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> ArrayValueExpression[
        Nullable[str], NullableValueExpression[str, StrValueExpression]
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct]]", instance: Any, owner: type["Table"]
    ) -> ArrayValueExpression[TStruct, StructValueExpression[TStruct]]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct | None]]", instance: Any, owner: type["Table"]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> ArrayValueExpression[
        Nullable[TStruct], StructNullableValueExpression[TStruct]
    ]: ...

    # --- Table owner: nullable arrays ---
    @overload
    def __get__(
        self: "Field[Array[bool] | None]", instance: Any, owner: type["Table"]
    ) -> ArrayNullableValueExpression[
        bool, BoolValueExpression, NullableValueExpression[bool, BoolValueExpression]
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[int] | None]", instance: Any, owner: type["Table"]
    ) -> ArrayNullableValueExpression[
        int, IntValueExpression, NullableValueExpression[int, IntValueExpression]
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[float] | None]", instance: Any, owner: type["Table"]
    ) -> ArrayNullableValueExpression[
        float,
        FloatValueExpression,
        NullableValueExpression[float, FloatValueExpression],
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[str] | None]", instance: Any, owner: type["Table"]
    ) -> ArrayNullableValueExpression[
        str, StrValueExpression, NullableValueExpression[str, StrValueExpression]
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[bool | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type["Table"],
    ) -> ArrayNullableValueExpression[
        Nullable[bool],
        NullableValueExpression[bool, BoolValueExpression],
        NullableValueExpression[bool, BoolValueExpression],
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[int | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type["Table"],
    ) -> ArrayNullableValueExpression[
        Nullable[int],
        NullableValueExpression[int, IntValueExpression],
        NullableValueExpression[int, IntValueExpression],
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[float | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type["Table"],
    ) -> ArrayNullableValueExpression[
        Nullable[float],
        NullableValueExpression[float, FloatValueExpression],
        NullableValueExpression[float, FloatValueExpression],
    ]: ...
    @overload
    def __get__(
        self: "Field[Array[str | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type["Table"],
    ) -> ArrayNullableValueExpression[
        Nullable[str],
        NullableValueExpression[str, StrValueExpression],
        NullableValueExpression[str, StrValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct] | None]", instance: Any, owner: type["Table"]
    ) -> ArrayNullableValueExpression[
        TStruct,
        StructValueExpression[TStruct],
        StructNullableValueExpression[TStruct],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[TStruct | None] | None]",  # pyright: ignore[reportInvalidTypeArguments]
        instance: Any,
        owner: type["Table"],
    ) -> ArrayNullableValueExpression[
        Nullable[TStruct],
        StructNullableValueExpression[TStruct],
        StructNullableValueExpression[TStruct],
    ]: ...

    # --- Table owner: structs ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[TStruct]", instance: Any, owner: type["Table"]
    ) -> StructValueExpression[TStruct]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[TStruct | None]", instance: Any, owner: type["Table"]
    ) -> StructNullableValueExpression[TStruct]: ...

    # --- Struct owner: non-null units ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[bool]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        BoolValueExpression,
        NullableValueExpression[bool, BoolValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[int]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        IntValueExpression,
        NullableValueExpression[int, IntValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[float]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        FloatValueExpression,
        NullableValueExpression[float, FloatValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[str]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        StrValueExpression,
        NullableValueExpression[str, StrValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct, TType: CustomDataType](
        self: "Field[TType]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        CustomDataTypeValueExpression[TType],
        NullableValueExpression[TType, CustomDataTypeValueExpression[TType]],
    ]: ...

    # --- Struct owner: nullable units ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[bool | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        NullableValueExpression[bool, BoolValueExpression],
        NullableValueExpression[bool, BoolValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[int | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        NullableValueExpression[int, IntValueExpression],
        NullableValueExpression[int, IntValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[float | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        NullableValueExpression[float, FloatValueExpression],
        NullableValueExpression[float, FloatValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[str | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        NullableValueExpression[str, StrValueExpression],
        NullableValueExpression[str, StrValueExpression],
    ]: ...
    @overload
    def __get__[TStruct: Struct, TType: CustomDataType](
        self: "Field[TType | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        NullableValueExpression[TType, CustomDataTypeValueExpression[TType]],
        NullableValueExpression[TType, CustomDataTypeValueExpression[TType]],
    ]: ...

    # --- Struct owner: arrays ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[bool]]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[bool, BoolValueExpression],
        ArrayNullableValueExpression[
            bool, BoolValueExpression, NullableValueExpression[bool, BoolValueExpression]
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[int]]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[int, IntValueExpression],
        ArrayNullableValueExpression[
            int, IntValueExpression, NullableValueExpression[int, IntValueExpression]
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[float]]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[float, FloatValueExpression],
        ArrayNullableValueExpression[
            float,
            FloatValueExpression,
            NullableValueExpression[float, FloatValueExpression],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[str]]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[str, StrValueExpression],
        ArrayNullableValueExpression[
            str, StrValueExpression, NullableValueExpression[str, StrValueExpression]
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[bool | None]]", instance: Any, owner: type[TStruct]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[
            Nullable[bool], NullableValueExpression[bool, BoolValueExpression]
        ],
        ArrayNullableValueExpression[
            Nullable[bool],
            NullableValueExpression[bool, BoolValueExpression],
            NullableValueExpression[bool, BoolValueExpression],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[int | None]]", instance: Any, owner: type[TStruct]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[
            Nullable[int], NullableValueExpression[int, IntValueExpression]
        ],
        ArrayNullableValueExpression[
            Nullable[int],
            NullableValueExpression[int, IntValueExpression],
            NullableValueExpression[int, IntValueExpression],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[float | None]]", instance: Any, owner: type[TStruct]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[
            Nullable[float], NullableValueExpression[float, FloatValueExpression]
        ],
        ArrayNullableValueExpression[
            Nullable[float],
            NullableValueExpression[float, FloatValueExpression],
            NullableValueExpression[float, FloatValueExpression],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[str | None]]", instance: Any, owner: type[TStruct]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[
            Nullable[str], NullableValueExpression[str, StrValueExpression]
        ],
        ArrayNullableValueExpression[
            Nullable[str],
            NullableValueExpression[str, StrValueExpression],
            NullableValueExpression[str, StrValueExpression],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct, TInner: Struct](
        self: "Field[Array[TInner]]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[TInner, StructValueExpression[TInner]],
        ArrayNullableValueExpression[
            TInner,
            StructValueExpression[TInner],
            StructNullableValueExpression[TInner],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct, TInner: Struct](
        self: "Field[Array[TInner | None]]", instance: Any, owner: type[TStruct]  # pyright: ignore[reportInvalidTypeArguments]
    ) -> PickedField[
        TStruct,
        ArrayValueExpression[Nullable[TInner], StructNullableValueExpression[TInner]],
        ArrayNullableValueExpression[
            Nullable[TInner],
            StructNullableValueExpression[TInner],
            StructNullableValueExpression[TInner],
        ],
    ]: ...

    # --- Struct owner: nullable arrays ---
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[bool] | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayNullableValueExpression[
            bool, BoolValueExpression, NullableValueExpression[bool, BoolValueExpression]
        ],
        ArrayNullableValueExpression[
            bool, BoolValueExpression, NullableValueExpression[bool, BoolValueExpression]
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[int] | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayNullableValueExpression[
            int, IntValueExpression, NullableValueExpression[int, IntValueExpression]
        ],
        ArrayNullableValueExpression[
            int, IntValueExpression, NullableValueExpression[int, IntValueExpression]
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[float] | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayNullableValueExpression[
            float,
            FloatValueExpression,
            NullableValueExpression[float, FloatValueExpression],
        ],
        ArrayNullableValueExpression[
            float,
            FloatValueExpression,
            NullableValueExpression[float, FloatValueExpression],
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct](
        self: "Field[Array[str] | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayNullableValueExpression[
            str, StrValueExpression, NullableValueExpression[str, StrValueExpression]
        ],
        ArrayNullableValueExpression[
            str, StrValueExpression, NullableValueExpression[str, StrValueExpression]
        ],
    ]: ...
    @overload
    def __get__[TStruct: Struct, TInner: Struct](
        self: "Field[Array[TInner] | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        ArrayNullableValueExpression[
            TInner,
            StructValueExpression[TInner],
            StructNullableValueExpression[TInner],
        ],
        ArrayNullableValueExpression[
            TInner,
            StructValueExpression[TInner],
            StructNullableValueExpression[TInner],
        ],
    ]: ...

    # --- Struct owner: nested structs ---
    @overload
    def __get__[TStruct: Struct, TInner: Struct](
        self: "Field[TInner]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        StructValueExpression[TInner],
        StructNullableValueExpression[TInner],
    ]: ...
    @overload
    def __get__[TStruct: Struct, TInner: Struct](
        self: "Field[TInner | None]", instance: Any, owner: type[TStruct]
    ) -> PickedField[
        TStruct,
        StructNullableValueExpression[TInner],
        StructNullableValueExpression[TInner],
    ]: ...

    def __get__(self, instance: Any, owner: Any) -> Any: ...


def field[TType: AuthoringDataType]() -> Field[TType]: ...  # pyright: ignore[reportInvalidTypeVarUse]
