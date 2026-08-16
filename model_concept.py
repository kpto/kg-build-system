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
# Expressions: specialised bindable ops (only via ValuePlan.value)
# ---------------------------------------------------------------------------


class ValueExpression[TType: NullableDataType]:
    """Bindable output. Obtained from ValuePlan.value."""


class NullableValueExpression[
    TData: DataType,
    TNonNullExpr: ValueExpression[Any],
](ValueExpression[Nullable[TData]]):
    """Bindable nullable value (null policy lives on NullableValuePlan)."""


class NumberValueExpression[TType: (int, float)](ValueExpression[TType]):
    def add(
        self, other: TType | ValueExpression[TType]
    ) -> "NumberValueExpression[TType]": ...
    def sub(
        self, other: TType | ValueExpression[TType]
    ) -> "NumberValueExpression[TType]": ...


class IntValueExpression(NumberValueExpression[int]):
    def add(self, other: int | ValueExpression[int]) -> "IntValueExpression": ...
    def sub(self, other: int | ValueExpression[int]) -> "IntValueExpression": ...


class FloatValueExpression(NumberValueExpression[float]):
    def add(self, other: float | ValueExpression[float]) -> "FloatValueExpression": ...
    def sub(self, other: float | ValueExpression[float]) -> "FloatValueExpression": ...


class BoolValueExpression(ValueExpression[bool]):
    def not_(self) -> "BoolValueExpression": ...
    def and_(self, other: bool | ValueExpression[bool]) -> "BoolValueExpression": ...
    def or_(self, other: bool | ValueExpression[bool]) -> "BoolValueExpression": ...


class StrValueExpression(ValueExpression[str]):
    def prepend(self, value: str | ValueExpression[str]) -> "StrValueExpression": ...
    def append(self, value: str | ValueExpression[str]) -> "StrValueExpression": ...


class CustomDataTypeValueExpression[TType: CustomDataType](ValueExpression[TType]): ...


class ArrayValueExpression[TItem: NullableDataType](ValueExpression[Array[TItem]]): ...


class StructValueExpression[TStruct: Struct](ValueExpression[TStruct]): ...


# ---------------------------------------------------------------------------
# ValuePlan[T]: generic handle; .value specialises the expression.
# Three structural specialisations: Nullable / Array / Struct.
# Plan ops use UnitType (not per-scalar overload matrices).
# ---------------------------------------------------------------------------


class ValuePlanValueDescriptor:
    """ValuePlan.value → specialised expression for T.

    Unit cases are listed individually: a TypeVar bound to UnitType cannot
    select BoolValueExpression vs IntValueExpression vs ….
    """

    @overload
    def __get__(
        self, instance: "ValuePlan[bool]", owner: type[Any] | None
    ) -> BoolValueExpression: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[int]", owner: type[Any] | None
    ) -> IntValueExpression: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[float]", owner: type[Any] | None
    ) -> FloatValueExpression: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[str]", owner: type[Any] | None
    ) -> StrValueExpression: ...
    @overload
    def __get__[TType: CustomDataType](
        self, instance: "ValuePlan[TType]", owner: type[Any] | None
    ) -> CustomDataTypeValueExpression[TType]: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[Nullable[bool]]", owner: type[Any] | None
    ) -> NullableValueExpression[bool, BoolValueExpression]: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[Nullable[int]]", owner: type[Any] | None
    ) -> NullableValueExpression[int, IntValueExpression]: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[Nullable[float]]", owner: type[Any] | None
    ) -> NullableValueExpression[float, FloatValueExpression]: ...
    @overload
    def __get__(
        self, instance: "ValuePlan[Nullable[str]]", owner: type[Any] | None
    ) -> NullableValueExpression[str, StrValueExpression]: ...
    @overload
    def __get__[TType: CustomDataType](
        self, instance: "ValuePlan[Nullable[TType]]", owner: type[Any] | None
    ) -> NullableValueExpression[TType, CustomDataTypeValueExpression[TType]]: ...
    @overload
    def __get__[TItem: NullableDataType](
        self, instance: "ValuePlan[Array[TItem]]", owner: type[Any] | None
    ) -> ArrayValueExpression[TItem]: ...
    @overload
    def __get__[TItem: NullableDataType](
        self, instance: "ValuePlan[Nullable[Array[TItem]]]", owner: type[Any] | None
    ) -> NullableValueExpression[Array[TItem], ArrayValueExpression[TItem]]: ...
    @overload
    def __get__[TStruct: Struct](
        self, instance: "ValuePlan[TStruct]", owner: type[Any] | None
    ) -> StructValueExpression[TStruct]: ...
    @overload
    def __get__[TStruct: Struct](
        self, instance: "ValuePlan[Nullable[TStruct]]", owner: type[Any] | None
    ) -> NullableValueExpression[TStruct, StructValueExpression[TStruct]]: ...

    def __get__(self, instance: Any, owner: Any) -> Any: ...


class ValuePlan[TType: NullableDataType]:
    """Generic plan. Specialised expression only via `.value`."""

    value: ValuePlanValueDescriptor = ValuePlanValueDescriptor()


class NullableValuePlan[TData: DataType](ValuePlan[Nullable[TData]]):
    """Nullable plan: null handling. Returns a non-null plan for TData."""

    @overload
    def or_else[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableValuePlan[TUnit]",
        value: TUnit | ValueExpression[TUnit],
    ) -> ValuePlan[TUnit]: ...
    @overload
    def or_else[TItem: NullableDataType](
        self: "NullableValuePlan[Array[TItem]]",
        value: Array[TItem] | ValueExpression[Array[TItem]],
    ) -> "ArrayValuePlan[TItem]": ...
    @overload
    def or_else[TStruct: Struct](
        self: "NullableValuePlan[TStruct]",
        value: TStruct | ValueExpression[TStruct],
    ) -> "StructValuePlan[TStruct]": ...

    def or_else(self, value: Any) -> Any: ...

    @overload
    def when_present[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableValuePlan[TUnit]",
    ) -> ValuePlan[TUnit]: ...
    @overload
    def when_present[TItem: NullableDataType](
        self: "NullableValuePlan[Array[TItem]]",
    ) -> "ArrayValuePlan[TItem]": ...
    @overload
    def when_present[TStruct: Struct](
        self: "NullableValuePlan[TStruct]",
    ) -> "StructValuePlan[TStruct]": ...

    def when_present(self) -> Any:
        """Produce only when present; null means this mapping contributes nothing."""
        ...

    # Nullable array/struct: navigation without unwrapping first.
    @overload
    def each[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableValuePlan[Array[TUnit]]",
    ) -> ValuePlan[TUnit]: ...
    @overload
    def each[TUnit: UnitType](
        self: "NullableValuePlan[Array[Nullable[TUnit]]]",
    ) -> "NullableValuePlan[TUnit]": ...
    @overload
    def each[TItem: NullableDataType](
        self: "NullableValuePlan[Array[TItem]]",
    ) -> ValuePlan[TItem]: ...
    @overload
    def each[TItem: DataType](
        self: "NullableValuePlan[Array[Nullable[TItem]]]",
    ) -> "NullableValuePlan[TItem]": ...
    @overload
    def each[TStruct: Struct](
        self: "NullableValuePlan[Array[TStruct]]",
    ) -> "StructValuePlan[TStruct]": ...
    @overload
    def each[TStruct: Struct](
        self: "NullableValuePlan[Array[Nullable[TStruct]]]",
    ) -> "NullableValuePlan[TStruct]": ...

    def each(self) -> Any: ...

    @overload
    def pick[TStruct: Struct, TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "NullableValuePlan[TStruct]",
        expr: Callable[[TStruct], ValuePlan[TUnit]],
    ) -> "NullableValuePlan[TUnit]": ...
    @overload
    def pick[TStruct: Struct, TInnerData: DataType](
        self: "NullableValuePlan[TStruct]",
        expr: Callable[[TStruct], "NullableValuePlan[TInnerData]"],
    ) -> "NullableValuePlan[TInnerData]": ...
    @overload
    def pick[TStruct: Struct, TItem: NullableDataType](
        self: "NullableValuePlan[TStruct]",
        expr: Callable[[TStruct], "ArrayValuePlan[TItem]"],
    ) -> "NullableValuePlan[Array[TItem]]": ...
    @overload
    def pick[TStruct: Struct, TInner: Struct](
        self: "NullableValuePlan[TStruct]",
        expr: Callable[[TStruct], "StructValuePlan[TInner]"],
    ) -> "NullableValuePlan[TInner]": ...

    def pick(self, expr: Any) -> Any: ...


class ArrayValuePlan[TItem: NullableDataType](ValuePlan[Array[TItem]]):
    """Array plan: element navigation via each."""

    @overload
    def each[TUnit: UnitType](  # pyright: ignore[reportOverlappingOverload]
        self: "ArrayValuePlan[TUnit]",
    ) -> ValuePlan[TUnit]: ...
    @overload
    def each[TUnit: UnitType](
        self: "ArrayValuePlan[Nullable[TUnit]]",
    ) -> "NullableValuePlan[TUnit]": ...
    @overload
    def each[TStruct: Struct](
        self: "ArrayValuePlan[TStruct]",
    ) -> "StructValuePlan[TStruct]": ...
    @overload
    def each[TStruct: Struct](
        self: "ArrayValuePlan[Nullable[TStruct]]",
    ) -> "NullableValuePlan[TStruct]": ...
    @overload
    def each[TInnerItem: NullableDataType](
        self: "ArrayValuePlan[Array[TInnerItem]]",
    ) -> "ArrayValuePlan[TInnerItem]": ...

    def each(self) -> Any: ...


class StructValuePlan[TStruct: Struct](ValuePlan[TStruct]):
    """Struct plan: member navigation via pick."""

    @overload
    def pick[TItem: NullableDataType](  # pyright: ignore[reportOverlappingOverload]
        self, expr: Callable[[TStruct], ArrayValuePlan[TItem]]
    ) -> ArrayValuePlan[TItem]: ...
    @overload
    def pick[TInner: Struct](
        self, expr: Callable[[TStruct], "StructValuePlan[TInner]"]
    ) -> "StructValuePlan[TInner]": ...
    @overload
    def pick[TData: DataType](
        self, expr: Callable[[TStruct], NullableValuePlan[TData]]
    ) -> NullableValuePlan[TData]: ...
    @overload
    def pick[TUnit: UnitType](
        self, expr: Callable[[TStruct], ValuePlan[TUnit]]
    ) -> ValuePlan[TUnit]: ...

    def pick(self, expr: Any) -> Any: ...


# Table is a Struct: same Field access path for roots and nested shapes.
class Table(Struct): ...
