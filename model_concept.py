from collections.abc import Callable
from typing import Any, Generic, TypeVar

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


# expression
class ValueExpression[TType: NullableDataType]:
    """Bindable output. No type-specific operators here."""


class NullableValueExpression[
    TData: DataType,
    TNonNullExpr: ValueExpression[Any],
](ValueExpression[Nullable[TData]]):
    """Nullable value: only null-handling operators until narrowed."""

    def or_else(self, value: TData | ValueExpression[TData]) -> TNonNullExpr: ...
    def when_present(self) -> TNonNullExpr:
        """Produce only when present; null means this mapping contributes nothing."""
        ...


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


# Path token: carries non-null and null-propagated expression types.
class PickedField[
    TStruct: Struct,
    TExpr: ValueExpression[Any],
    TNullExpr: ValueExpression[Any],
]: ...


class ArrayValueExpression[
    TItem: NullableDataType,
    TItemExpr: ValueExpression[Any],
](ValueExpression[Array[TItem]]):
    def each(self) -> TItemExpr: ...


class ArrayNullableValueExpression[
    TItem: NullableDataType,
    TItemExpr: ValueExpression[Any],
    TItemNullExpr: ValueExpression[Any],  # reserved: future null-array each variant
](
    NullableValueExpression[Array[TItem], ArrayValueExpression[TItem, TItemExpr]],
):
    # Null array does not produce; item nullability unchanged.
    def each(self) -> TItemExpr: ...


class StructValueExpression[TStruct: Struct](ValueExpression[TStruct]):
    def pick[TExpr: ValueExpression[Any], TNullExpr: ValueExpression[Any]](
        self,
        expr: Callable[[TStruct], PickedField[TStruct, TExpr, TNullExpr]],
    ) -> TExpr: ...


class StructNullableValueExpression[TStruct: Struct](
    NullableValueExpression[TStruct, StructValueExpression[TStruct]],
):
    def pick[TExpr: ValueExpression[Any], TNullExpr: ValueExpression[Any]](
        self,
        expr: Callable[[TStruct], PickedField[TStruct, TExpr, TNullExpr]],
    ) -> TNullExpr: ...


# table
class Table: ...
