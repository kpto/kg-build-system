from collections.abc import Callable
from typing import Any, Generic, TypeVar, overload

type UnitType = str | int | float | bool | CustomDataType
type StructuredType = Array[NullableDataType] | Struct
type DataType = UnitType | StructuredType

type NullableUnitType = UnitType | Nullable[UnitType]
type NullableStructuredType = StructuredType | Nullable[StructuredType]
type NullableDataType = DataType | Nullable[DataType]


# core
TArray_co = TypeVar("TArray_co", bound=NullableDataType, covariant=True)


class Nullable[T: DataType]: ...


class Array(Generic[TArray_co]): ...


class Struct: ...


class CustomDataType: ...


# ---------------------------------------------------------------------------
# Expressions: specialised bindable calculations exposed by a selection
# ---------------------------------------------------------------------------


class ValueExpression[TType: NullableDataType]:
    """Bindable calculation exposed by ``ValueSelection.expression``."""


class NullableExpression[
    TData: DataType,
    TNonNullExpr: ValueExpression[Any],
](ValueExpression[Nullable[TData]]):
    """Bindable nullable value (null policy lives on ``NullableSelection``)."""


class NumberExpression[TType: (int, float)](ValueExpression[TType]):
    def add(
        self, other: TType | ValueExpression[TType]
    ) -> "NumberExpression[TType]": ...
    def sub(
        self, other: TType | ValueExpression[TType]
    ) -> "NumberExpression[TType]": ...


class IntExpression(NumberExpression[int]):
    def add(self, other: int | ValueExpression[int]) -> "IntExpression": ...
    def sub(self, other: int | ValueExpression[int]) -> "IntExpression": ...


class FloatExpression(NumberExpression[float]):
    def add(self, other: float | ValueExpression[float]) -> "FloatExpression": ...
    def sub(self, other: float | ValueExpression[float]) -> "FloatExpression": ...


class BoolExpression(ValueExpression[bool]):
    def not_(self) -> "BoolExpression": ...
    def and_(self, other: bool | ValueExpression[bool]) -> "BoolExpression": ...
    def or_(self, other: bool | ValueExpression[bool]) -> "BoolExpression": ...


class StrExpression(ValueExpression[str]):
    def prepend(self, value: str | ValueExpression[str]) -> "StrExpression": ...
    def append(self, value: str | ValueExpression[str]) -> "StrExpression": ...


class CustomDataTypeExpression[TType: CustomDataType](ValueExpression[TType]): ...


class ArrayExpression[TItem: NullableDataType](ValueExpression[Array[TItem]]): ...


class StructExpression[TStruct: Struct](ValueExpression[TStruct]): ...


# ---------------------------------------------------------------------------
# ValueSelection[T]: structural and null-aware selection whose .expression
# exposes a specialised bindable calculation.
# Three structural specialisations: Nullable / Array / Struct.
# Selection ops use UnitType (not per-scalar overload matrices).
# ---------------------------------------------------------------------------


class _ExpressionDescriptor:
    """ValueSelection.expression → specialised expression for T.

    Unit cases are listed individually: a TypeVar bound to UnitType cannot
    select BoolExpression vs IntExpression vs ….
    """

    @overload
    def __get__(
        self, instance: "ValueSelection[bool]", owner: type[Any] | None
    ) -> BoolExpression: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[int]", owner: type[Any] | None
    ) -> IntExpression: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[float]", owner: type[Any] | None
    ) -> FloatExpression: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[str]", owner: type[Any] | None
    ) -> StrExpression: ...
    @overload
    def __get__[TType: CustomDataType](
        self, instance: "ValueSelection[TType]", owner: type[Any] | None
    ) -> CustomDataTypeExpression[TType]: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[Nullable[bool]]", owner: type[Any] | None
    ) -> NullableExpression[bool, BoolExpression]: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[Nullable[int]]", owner: type[Any] | None
    ) -> NullableExpression[int, IntExpression]: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[Nullable[float]]", owner: type[Any] | None
    ) -> NullableExpression[float, FloatExpression]: ...
    @overload
    def __get__(
        self, instance: "ValueSelection[Nullable[str]]", owner: type[Any] | None
    ) -> NullableExpression[str, StrExpression]: ...
    @overload
    def __get__[TType: CustomDataType](
        self, instance: "ValueSelection[Nullable[TType]]", owner: type[Any] | None
    ) -> NullableExpression[TType, CustomDataTypeExpression[TType]]: ...
    @overload
    def __get__[TItem: NullableDataType](
        self, instance: "ValueSelection[Array[TItem]]", owner: type[Any] | None
    ) -> ArrayExpression[TItem]: ...
    @overload
    def __get__[TItem: NullableDataType](
        self, instance: "ValueSelection[Nullable[Array[TItem]]]", owner: type[Any] | None
    ) -> NullableExpression[Array[TItem], ArrayExpression[TItem]]: ...
    @overload
    def __get__[TStruct: Struct](
        self, instance: "ValueSelection[TStruct]", owner: type[Any] | None
    ) -> StructExpression[TStruct]: ...
    @overload
    def __get__[TStruct: Struct](
        self, instance: "ValueSelection[Nullable[TStruct]]", owner: type[Any] | None
    ) -> NullableExpression[TStruct, StructExpression[TStruct]]: ...

    def __get__(self, instance: Any, owner: Any) -> Any: ...


class ValueSelection[TType: NullableDataType]:
    """Generic selection. Bindable calculation exposed through `.expression`."""

    expression: _ExpressionDescriptor = _ExpressionDescriptor()


class NullableSelection[TData: DataType](ValueSelection[Nullable[TData]]):
    """Nullable selection whose null policy returns a non-null selection."""

    @overload
    def default_to[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableSelection[TUnit]",
        value: TUnit | ValueExpression[TUnit],
    ) -> ValueSelection[TUnit]: ...
    @overload
    def default_to[TItem: NullableDataType](
        self: "NullableSelection[Array[TItem]]",
        value: Array[TItem] | ValueExpression[Array[TItem]],
    ) -> "ArraySelection[TItem]": ...
    @overload
    def default_to[TStruct: Struct](
        self: "NullableSelection[TStruct]",
        value: TStruct | ValueExpression[TStruct],
    ) -> "StructSelection[TStruct]": ...

    def default_to(self, value: Any) -> Any: ...

    @overload
    def where_present[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableSelection[TUnit]",
    ) -> ValueSelection[TUnit]: ...
    @overload
    def where_present[TItem: NullableDataType](
        self: "NullableSelection[Array[TItem]]",
    ) -> "ArraySelection[TItem]": ...
    @overload
    def where_present[TStruct: Struct](
        self: "NullableSelection[TStruct]",
    ) -> "StructSelection[TStruct]": ...

    def where_present(self) -> Any:
        """Retain only rows where this selection is present."""
        ...

    # Nullable arrays and structs support navigation without first defaulting.
    @overload
    def expand[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableSelection[Array[TUnit]]",
    ) -> ValueSelection[TUnit]: ...
    @overload
    def expand[TUnit: UnitType](
        self: "NullableSelection[Array[Nullable[TUnit]]]",
    ) -> "NullableSelection[TUnit]": ...
    @overload
    def expand[TItem: NullableDataType](
        self: "NullableSelection[Array[TItem]]",
    ) -> ValueSelection[TItem]: ...
    @overload
    def expand[TItem: DataType](
        self: "NullableSelection[Array[Nullable[TItem]]]",
    ) -> "NullableSelection[TItem]": ...
    @overload
    def expand[TStruct: Struct](
        self: "NullableSelection[Array[TStruct]]",
    ) -> "StructSelection[TStruct]": ...
    @overload
    def expand[TStruct: Struct](
        self: "NullableSelection[Array[Nullable[TStruct]]]",
    ) -> "NullableSelection[TStruct]": ...

    def expand(self) -> Any: ...

    @overload
    def pick[TStruct: Struct, TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableSelection[TStruct]",
        expr: Callable[[TStruct], ValueSelection[TUnit]],
    ) -> "NullableSelection[TUnit]": ...
    @overload
    def pick[TStruct: Struct, TInnerData: DataType](
        self: "NullableSelection[TStruct]",
        expr: Callable[[TStruct], "NullableSelection[TInnerData]"],
    ) -> "NullableSelection[TInnerData]": ...
    @overload
    def pick[TStruct: Struct, TItem: NullableDataType](
        self: "NullableSelection[TStruct]",
        expr: Callable[[TStruct], "ArraySelection[TItem]"],
    ) -> "NullableSelection[Array[TItem]]": ...
    @overload
    def pick[TStruct: Struct, TInner: Struct](
        self: "NullableSelection[TStruct]",
        expr: Callable[[TStruct], "StructSelection[TInner]"],
    ) -> "NullableSelection[TInner]": ...

    def pick(self, expr: Any) -> Any: ...


class ArraySelection[TItem: NullableDataType](ValueSelection[Array[TItem]]):
    """Array selection supporting row-producing item expansion."""

    @overload
    def expand[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "ArraySelection[TUnit]",
    ) -> ValueSelection[TUnit]: ...
    @overload
    def expand[TUnit: UnitType](
        self: "ArraySelection[Nullable[TUnit]]",
    ) -> "NullableSelection[TUnit]": ...
    @overload
    def expand[TStruct: Struct](
        self: "ArraySelection[TStruct]",
    ) -> "StructSelection[TStruct]": ...
    @overload
    def expand[TStruct: Struct](
        self: "ArraySelection[Nullable[TStruct]]",
    ) -> "NullableSelection[TStruct]": ...
    @overload
    def expand[TInnerItem: NullableDataType](
        self: "ArraySelection[Array[TInnerItem]]",
    ) -> "ArraySelection[TInnerItem]": ...

    def expand(self) -> Any: ...


class StructSelection[TStruct: Struct](ValueSelection[TStruct]):
    """Struct selection supporting declared-member navigation."""

    @overload
    def pick[TItem: NullableDataType](  # pyright: ignore[reportOverlappingOverload]
        self, expr: Callable[[TStruct], ArraySelection[TItem]]
    ) -> ArraySelection[TItem]: ...
    @overload
    def pick[TInner: Struct](
        self, expr: Callable[[TStruct], "StructSelection[TInner]"]
    ) -> "StructSelection[TInner]": ...
    @overload
    def pick[TData: DataType](
        self, expr: Callable[[TStruct], NullableSelection[TData]]
    ) -> NullableSelection[TData]: ...
    @overload
    def pick[TUnit: UnitType](
        self, expr: Callable[[TStruct], ValueSelection[TUnit]]
    ) -> ValueSelection[TUnit]: ...

    def pick(self, expr: Any) -> Any: ...


# Table is a Struct: same Field access path for roots and nested shapes.
class Table(Struct): ...
