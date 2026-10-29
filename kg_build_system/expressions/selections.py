"""Structural, null-aware selections over bindable expressions."""
from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Generic, Self, TypeVar, cast, overload

from ..types import (
    Array, ArrayType, CustomDataType, Date, LogicalType, Nullable, NullableType,
    STR, Struct, StructType, Time, Timestamp, Uuid,
)
from ._coercion import expression_input
from .base import field_reference, operation
from .codec import encode_expression
from .models import FieldReferenceExpression, OperationExpression, RowSemantics, Traversal
from .values import NullableAuthoringInput, ValueExpression


type SelectionUnit = bool | int | float | str | Date | Time | Timestamp | Uuid | CustomDataType
type SelectionStructured = Array[NullableDataType] | Struct
type SelectionDataType = SelectionUnit | SelectionStructured
type NullableDataType = SelectionDataType | Nullable[SelectionDataType]

TType_co = TypeVar("TType_co", covariant=True)
TItem = TypeVar("TItem")
TStruct = TypeVar("TStruct", bound=Struct)


@dataclass(frozen=True, slots=True)
class _SelectedMember:
    name: str
    logical_type: LogicalType
    declaration: StructType


class _ExpressionDescriptor:
    @overload
    def __get__(self, instance: "ValueSelection[bool]", owner: type[Any] | None) -> "BoolExpression": ...
    @overload
    def __get__(self, instance: "ValueSelection[int]", owner: type[Any] | None) -> "IntExpression": ...
    @overload
    def __get__(self, instance: "ValueSelection[float]", owner: type[Any] | None) -> "FloatExpression": ...
    @overload
    def __get__(self, instance: "ValueSelection[str]", owner: type[Any] | None) -> "StrExpression": ...
    @overload
    def __get__[C: CustomDataType](self, instance: "ValueSelection[C]", owner: type[Any] | None) -> "CustomDataTypeExpression[C]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[bool]]", owner: type[Any] | None) -> "NullableExpression[bool, BoolExpression]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[int]]", owner: type[Any] | None) -> "NullableExpression[int, IntExpression]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[float]]", owner: type[Any] | None) -> "NullableExpression[float, FloatExpression]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[str]]", owner: type[Any] | None) -> "NullableExpression[str, StrExpression]": ...
    @overload
    def __get__[C: CustomDataType](self, instance: "ValueSelection[Nullable[C]]", owner: type[Any] | None) -> "NullableExpression[C, CustomDataTypeExpression[C]]": ...
    @overload
    def __get__[I: NullableDataType](self, instance: "ValueSelection[Array[I]]", owner: type[Any] | None) -> "ArrayExpression[I]": ...
    @overload
    def __get__[I: NullableDataType](self, instance: "ValueSelection[Nullable[Array[I]]]", owner: type[Any] | None) -> "NullableExpression[Array[I], ArrayExpression[I]]": ...
    @overload
    def __get__[S: Struct](self, instance: "ValueSelection[S]", owner: type[Any] | None) -> "StructExpression[S]": ...
    @overload
    def __get__[S: Struct](self, instance: "ValueSelection[Nullable[S]]", owner: type[Any] | None) -> "NullableExpression[S, StructExpression[S]]": ...
    @overload
    def __get__[T](self, instance: "ValueSelection[T]", owner: type[Any] | None) -> ValueExpression[T]: ...  # pyright: ignore[reportOverlappingOverload]

    def __get__(self, instance: Any, owner: Any) -> Any:
        if instance is None:
            return self
        return instance._require_expression()


class ValueSelection(Generic[TType_co]):
    """A selectable value whose bindable calculation is exposed by ``expression``."""

    __slots__ = ("_value", "_member")
    expression: _ExpressionDescriptor = _ExpressionDescriptor()

    def __init__(
        self,
        value: ValueExpression[Any] | None = None,
        *,
        member: _SelectedMember | None = None,
    ) -> None:
        if (value is None) == (member is None):
            raise TypeError("a selection requires exactly one expression or selected member")
        self._value = value
        self._member = member

    def drop_if(self, predicate: "Callable[[Self], BoolExpression]") -> Self:
        """Keep rows whose value satisfies a value-scoped predicate."""
        if not callable(predicate):
            raise TypeError("drop_if requires a callable predicate")
        result = predicate(self)
        if not isinstance(result, BoolExpression):
            raise TypeError("drop_if predicates must return a BoolExpression")
        from .factory import wrap_expression

        model = operation(
            "where_if",
            self._require_expression().model,
            result.model,
            logical_type=self.logical_type,
            row_semantics=RowSemantics("filter"),
        )
        return cast(Self, select_expression(wrap_expression(model)))

    def alter_rows(self) -> "RowEffects[Self]":
        """Opt in to the row-changing operations available on this selection."""
        return RowEffects(self)

    @property
    def logical_type(self) -> LogicalType:
        return self._value.logical_type if self._value is not None else cast(_SelectedMember, self._member).logical_type

    def _require_expression(self) -> ValueExpression[Any]:
        if self._value is None:
            raise TypeError("a struct member selection is only valid inside extract")
        return self._value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value or self._member!r})"


class NullableSelection(
    ValueSelection[Nullable[TItem]], NullableAuthoringInput[TItem | None], Generic[TItem]
):
    """Nullable selection owning explicit null policy and nullable navigation."""

    @overload
    def default_to[U: SelectionUnit](
        self: "NullableSelection[U]", value: U | ValueExpression[U],
    ) -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def default_to[I: NullableDataType](
        self: "NullableSelection[Array[I]]", value: Array[I] | ValueExpression[Array[I]],
    ) -> "ArraySelection[I]": ...
    @overload
    def default_to[S: Struct](
        self: "NullableSelection[S]", value: S | ValueExpression[S],
    ) -> "StructSelection[S]": ...
    def default_to(self, value: Any) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType):
            raise TypeError("default_to requires a nullable selection")
        from ._coercion import expression_input
        from .factory import wrap_expression

        normalized = as_expression(value) if isinstance(value, (ValueSelection, ValueExpression)) else value
        fallback = expression_input(normalized, logical_type.value)
        result = operation(
            "coalesce", self._require_expression().model, fallback, logical_type=logical_type.value,
        )
        return select_expression(wrap_expression(result))

    @overload
    def drop_null[U: SelectionUnit](self: "NullableSelection[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def drop_null[I: NullableDataType](self: "NullableSelection[Array[I]]") -> "ArraySelection[I]": ...
    @overload
    def drop_null[S: Struct](self: "NullableSelection[S]") -> "StructSelection[S]": ...
    def drop_null(self) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType):
            raise TypeError("drop_null requires a nullable selection")
        from .factory import wrap_expression

        result = operation(
            "where_present",
            self._require_expression().model,
            logical_type=logical_type.value,
            row_semantics=RowSemantics("filter"),
        )
        return select_expression(wrap_expression(result))

    where_present = drop_null

    @overload
    def at[I: NullableDataType](
        self: "NullableSelection[Array[Nullable[I]]]", index: int | ValueInput[int],
    ) -> "NullableSelection[I]": ...
    @overload
    def at[I: NullableDataType](
        self: "NullableSelection[Array[I]]", index: int | ValueInput[int],
    ) -> "NullableSelection[I]": ...
    def at(self, index: int | ValueInput[int]) -> ValueSelection[Any]:
        from ._coercion import expression_input
        from ..types import INT

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("at requires a nullable array selection")
        item = logical_type.value.item
        result_type = item if isinstance(item, NullableType) else NullableType(item)
        model = operation(
            "array_at",
            self._require_expression().model,
            expression_input(index, INT),
            logical_type=result_type,
        )
        from .factory import wrap_expression

        return select_expression(wrap_expression(model))

    @overload
    def slice[I: NullableDataType](
        self: "NullableSelection[Array[Nullable[I]]]",
        start: int | ValueInput[int],
        end: int | ValueInput[int],
    ) -> "NullableSelection[Array[Nullable[I]]]": ...
    @overload
    def slice[I: NullableDataType](
        self: "NullableSelection[Array[I]]",
        start: int | ValueInput[int],
        end: int | ValueInput[int],
    ) -> "NullableSelection[Array[I]]": ...
    def slice(self, start: int | ValueInput[int], end: int | ValueInput[int]) -> ValueSelection[Any]:
        from ._coercion import expression_input
        from ..types import INT

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("slice requires a nullable array selection")
        model = operation(
            "array_slice",
            self._require_expression().model,
            expression_input(start, INT),
            expression_input(end, INT),
            logical_type=logical_type,
        )
        from .factory import wrap_expression

        return select_expression(wrap_expression(model))

    def alter_rows(self) -> "NullableRowEffects[TItem]":
        return NullableRowEffects(self)

    @overload
    def expand[U: SelectionUnit](self: "NullableSelection[Array[U]]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "NullableSelection[Array[Nullable[U]]]") -> "NullableSelection[U]": ...
    @overload
    def expand[S: Struct](self: "NullableSelection[Array[S]]") -> "StructSelection[S]": ...
    @overload
    def expand[S: Struct](self: "NullableSelection[Array[Nullable[S]]]") -> "NullableSelection[S]": ...
    @overload
    def expand[I: NullableDataType](self: "NullableSelection[Array[Array[I]]]") -> "ArraySelection[I]": ...
    def expand(self) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("expand requires a nullable array selection")
        return _expand(self._require_expression(), logical_type.value)

    @overload
    def extract[S: Struct, U: SelectionUnit](
        self: "NullableSelection[S]", selector: Callable[[S], ValueSelection[U]],
    ) -> "NullableSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def extract[S: Struct, D: SelectionDataType](
        self: "NullableSelection[S]", selector: Callable[[S], "NullableSelection[D]"],
    ) -> "NullableSelection[D]": ...
    @overload
    def extract[S: Struct, I: NullableDataType](
        self: "NullableSelection[S]", selector: Callable[[S], "ArraySelection[I]"],
    ) -> "NullableSelection[Array[I]]": ...
    @overload
    def extract[S: Struct, Inner: Struct](
        self: "NullableSelection[S]", selector: Callable[[S], "StructSelection[Inner]"],
    ) -> "NullableSelection[Inner]": ...
    def extract(self, selector: Callable[[Any], ValueSelection[Any]]) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, StructType):
            raise TypeError("extract requires a nullable struct selection")
        return _pick(self, selector, logical_type.value, propagate_null=True)

    pick = extract

    @overload
    def transform_items[S: Struct, U](
        self: "NullableSelection[Array[S]]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "NullableSelection[Array[U]]": ...
    @overload
    def transform_items[U](
        self: "NullableSelection[Array[TItem]]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "NullableSelection[Array[U]]": ...
    @overload
    def transform_items[S: Struct, U](
        self: "NullableSelection[Array[Nullable[S]]]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "NullableSelection[Array[Nullable[U]]]": ...
    @overload
    def transform_items[U](
        self: "NullableSelection[Array[Nullable[TItem]]]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "NullableSelection[Array[Nullable[U]]]": ...
    def transform_items(self, selector: Callable[[Any], ValueExpression[Any]]) -> "NullableSelection[Any]":
        from .arrays import _transform_items

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("transform_items requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(_transform_items(self._require_expression(), selector)),
        )

    @overload
    def drop_null_items[I: NullableDataType](
        self: "NullableSelection[Array[Nullable[I]]]",
    ) -> "NullableSelection[Array[I]]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def drop_null_items[I: NullableDataType](
        self: "NullableSelection[Array[I]]",
    ) -> "NullableSelection[Array[I]]": ...
    def drop_null_items(self) -> "NullableSelection[Any]":
        from .arrays import _drop_null_items

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("drop_null_items requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(_drop_null_items(self._require_expression())),
        )

    def sort(self) -> "NullableSelection[Any]":
        from .arrays import _array_operation

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("sort requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(_array_operation(self._require_expression(), "sort")),
        )

    def unique(self) -> "NullableSelection[Any]":
        from .arrays import _array_operation

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("unique requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(
                _array_operation(self._require_expression(), "distinct")
            ),
        )

    distinct = unique

    def concat(self, separator: str) -> "NullableSelection[str]":
        from .factory import wrap_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(logical_type.value, ArrayType):
            raise TypeError("concat requires a nullable array selection")
        if logical_type.value.item != STR:
            raise TypeError("concat requires an array of non-null strings")
        result = operation(
            "join",
            self._require_expression().model,
            expression_input(separator, STR),
            logical_type=NullableType(STR),
        )
        return cast("NullableSelection[str]", select_expression(wrap_expression(result)))

    join = concat


class ArraySelection(ValueSelection[Array[TItem]], Generic[TItem]):
    """Array selection supporting explicit row-producing expansion."""

    @overload
    def transform_items[S: Struct, U](
        self: "ArraySelection[S]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "ArraySelection[U]": ...
    @overload
    def transform_items[U](
        self: "ArraySelection[TItem]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "ArraySelection[U]": ...
    @overload
    def transform_items[S: Struct, U](
        self: "ArraySelection[Nullable[S]]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "ArraySelection[Nullable[U]]": ...
    @overload
    def transform_items[U](
        self: "ArraySelection[Nullable[TItem]]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "ArraySelection[Nullable[U]]": ...
    def transform_items(self, selector: Callable[[Any], ValueExpression[Any]]) -> "ArraySelection[Any]":
        from .arrays import ArrayExpression, _transform_items

        expression = self._require_expression()
        if not isinstance(expression, ArrayExpression):
            raise TypeError("transform_items requires an array selection")
        return cast(
            "ArraySelection[Any]",
            select_expression(_transform_items(expression, selector)),
        )

    @overload
    def drop_null_items[I: NullableDataType](
        self: "ArraySelection[Nullable[I]]",
    ) -> "ArraySelection[I]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def drop_null_items[I: NullableDataType](
        self: "ArraySelection[I]",
    ) -> "ArraySelection[I]": ...
    def drop_null_items(self) -> "ArraySelection[Any]":
        from .arrays import ArrayExpression, _drop_null_items

        expression = self._require_expression()
        if not isinstance(expression, ArrayExpression):
            raise TypeError("drop_null_items requires an array selection")
        return cast(
            "ArraySelection[Any]",
            select_expression(_drop_null_items(expression)),
        )

    def sort(self) -> "ArraySelection[TItem]":
        from .arrays import ArrayExpression, _array_operation

        expression = self._require_expression()
        if not isinstance(expression, ArrayExpression):
            raise TypeError("sort requires an array selection")
        return cast(
            "ArraySelection[TItem]",
            select_expression(_array_operation(expression, "sort")),
        )

    def unique(self) -> "ArraySelection[TItem]":
        from .arrays import ArrayExpression, _array_operation

        expression = self._require_expression()
        if not isinstance(expression, ArrayExpression):
            raise TypeError("unique requires an array selection")
        return cast(
            "ArraySelection[TItem]",
            select_expression(_array_operation(expression, "distinct")),
        )

    def concat(self, separator: str) -> ValueSelection[str]:
        from .arrays import ArrayExpression

        expression = self._require_expression()
        if not isinstance(expression, ArrayExpression):
            raise TypeError("concat requires an array selection")
        return select_expression(expression.join(separator))

    join = concat
    distinct = unique

    @overload
    def at[U: SelectionUnit](self: "ArraySelection[U]", index: int | ValueInput[int]) -> "NullableSelection[U]": ...
    @overload
    def at[U: SelectionUnit](self: "ArraySelection[Nullable[U]]", index: int | ValueInput[int]) -> "NullableSelection[U]": ...
    @overload
    def at[S: Struct](self: "ArraySelection[S]", index: int | ValueInput[int]) -> "NullableSelection[S]": ...
    @overload
    def at[S: Struct](self: "ArraySelection[Nullable[S]]", index: int | ValueInput[int]) -> "NullableSelection[S]": ...
    @overload
    def at[I: NullableDataType](self: "ArraySelection[Array[I]]", index: int | ValueInput[int]) -> "NullableSelection[Array[I]]": ...
    def at(self, index: int | ValueInput[int]) -> ValueSelection[Any]:
        from ._coercion import expression_input
        from ..types import INT

        logical_type = self.logical_type
        if not isinstance(logical_type, ArrayType):
            raise TypeError("at requires an array selection")
        item = logical_type.item
        result_type = item if isinstance(item, NullableType) else NullableType(item)
        model = operation(
            "array_at",
            self._require_expression().model,
            expression_input(index, INT),
            logical_type=result_type,
        )
        from .factory import wrap_expression

        return select_expression(wrap_expression(model))

    def slice(self, start: int | ValueInput[int], end: int | ValueInput[int]) -> "ArraySelection[TItem]":
        from ._coercion import expression_input
        from ..types import INT

        logical_type = self.logical_type
        if not isinstance(logical_type, ArrayType):
            raise TypeError("slice requires an array selection")
        model = operation(
            "array_slice",
            self._require_expression().model,
            expression_input(start, INT),
            expression_input(end, INT),
            logical_type=logical_type,
        )
        from .factory import wrap_expression

        return cast("ArraySelection[TItem]", select_expression(wrap_expression(model)))

    def alter_rows(self) -> "ArrayRowEffects[TItem]":
        return ArrayRowEffects(self)

    @overload
    def expand[U: SelectionUnit](self: "ArraySelection[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "ArraySelection[Nullable[U]]") -> NullableSelection[U]: ...
    @overload
    def expand[S: Struct](self: "ArraySelection[S]") -> "StructSelection[S]": ...
    @overload
    def expand[S: Struct](self: "ArraySelection[Nullable[S]]") -> NullableSelection[S]: ...
    @overload
    def expand[I: NullableDataType](self: "ArraySelection[Array[I]]") -> "ArraySelection[I]": ...
    def expand(self) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, ArrayType):
            raise TypeError("expand requires an array selection")
        return _expand(self._require_expression(), logical_type)


class StructSelection(ValueSelection[TStruct], Generic[TStruct]):
    """Struct selection supporting declared-member navigation."""

    @overload
    def extract[I: NullableDataType](self, selector: Callable[[TStruct], ArraySelection[I]]) -> ArraySelection[I]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def extract[Inner: Struct](self, selector: Callable[[TStruct], "StructSelection[Inner]"]) -> "StructSelection[Inner]": ...
    @overload
    def extract[D: SelectionDataType](self, selector: Callable[[TStruct], NullableSelection[D]]) -> NullableSelection[D]: ...
    @overload
    def extract[U: SelectionUnit](self, selector: Callable[[TStruct], ValueSelection[U]]) -> ValueSelection[U]: ...
    def extract(self, selector: Callable[[TStruct], ValueSelection[Any]]) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, StructType):
            raise TypeError("extract requires a struct selection")
        return _pick(self, selector, logical_type, propagate_null=False)

    pick = extract


SSelection = TypeVar("SSelection", bound="ValueSelection[Any]")


class RowEffects(Generic[SSelection]):
    """A one-shot opt-in to the row-changing operations of one selection.

    Every method consumes the permission: it returns a selection, not another
    handle, so a second row effect must opt in again.
    """

    __slots__ = ("_selection",)

    def __init__(self, selection: SSelection) -> None:
        self._selection = selection

    @property
    def selection(self) -> SSelection:
        return self._selection

    def drop_if(self, predicate: Callable[[SSelection], "BoolExpression"]) -> SSelection:
        """Drop rows whose value does not satisfy the predicate."""
        return self._selection.drop_if(predicate)


class ArrayRowEffects(RowEffects["ArraySelection[TItem]"], Generic[TItem]):
    """Row effects available on an array selection."""

    @overload
    def expand[U: SelectionUnit](self: "ArrayRowEffects[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "ArrayRowEffects[Nullable[U]]") -> NullableSelection[U]: ...
    @overload
    def expand[S: Struct](self: "ArrayRowEffects[S]") -> StructSelection[S]: ...
    @overload
    def expand[S: Struct](self: "ArrayRowEffects[Nullable[S]]") -> NullableSelection[S]: ...
    @overload
    def expand[I: NullableDataType](self: "ArrayRowEffects[Array[I]]") -> ArraySelection[I]: ...
    def expand(self) -> ValueSelection[Any]:
        """One row per array element."""
        return cast("ArraySelection[Any]", self._selection).expand()


class NullableRowEffects(RowEffects["NullableSelection[TItem]"], Generic[TItem]):
    """Row effects available on a nullable selection."""

    @overload
    def drop_null[U: SelectionUnit](self: "NullableRowEffects[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def drop_null[I: NullableDataType](self: "NullableRowEffects[Array[I]]") -> ArraySelection[I]: ...
    @overload
    def drop_null[S: Struct](self: "NullableRowEffects[S]") -> StructSelection[S]: ...
    def drop_null(self) -> ValueSelection[Any]:
        """Drop rows whose value is null."""
        return cast("NullableSelection[Any]", self._selection).drop_null()

    @overload
    def expand[U: SelectionUnit](self: "NullableRowEffects[Array[U]]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "NullableRowEffects[Array[Nullable[U]]]") -> NullableSelection[U]: ...
    @overload
    def expand[S: Struct](self: "NullableRowEffects[Array[S]]") -> StructSelection[S]: ...
    @overload
    def expand[S: Struct](self: "NullableRowEffects[Array[Nullable[S]]]") -> NullableSelection[S]: ...
    @overload
    def expand[I: NullableDataType](self: "NullableRowEffects[Array[Array[I]]]") -> ArraySelection[I]: ...
    def expand(self) -> ValueSelection[Any]:
        """One row per element of a present array."""
        return cast("NullableSelection[Array[Any]]", self._selection).expand()


type ValueInput[T] = ValueSelection[T] | ValueExpression[T]


def as_expression[T](value: ValueInput[T]) -> ValueExpression[T]:
    """Normalize a terminal authoring input to its bindable expression."""
    if isinstance(value, ValueSelection):
        return cast(ValueExpression[T], value._require_expression())
    if isinstance(value, ValueExpression):
        return value
    raise TypeError("expected a value selection or value expression")


def _declaration(logical_type: StructType) -> type[Struct]:
    value: Any = importlib.import_module(logical_type.module)
    for part in logical_type.qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type) or not issubclass(value, Struct):
        raise TypeError("struct logical type does not resolve to a Struct declaration")
    return value


def _pick(
    parent: ValueSelection[Any],
    selector: Callable[[Any], ValueSelection[Any]],
    parent_type: StructType,
    *,
    propagate_null: bool,
) -> ValueSelection[Any]:
    proxy = object.__new__(_declaration(parent_type))
    selected = selector(proxy)
    if not isinstance(selected, ValueSelection) or selected._member is None:
        raise TypeError("struct selectors must return a declared field selection")
    member = selected._member
    if member.declaration != parent_type:
        raise TypeError("struct selectors must return a field from their input declaration")
    result_type = member.logical_type
    if propagate_null and not isinstance(result_type, NullableType):
        result_type = NullableType(result_type)
    parent_model = parent._require_expression().model
    if isinstance(parent_model, FieldReferenceExpression):
        path = (*parent_model.path, member.name)
        traversals = list(parent_model.traversals)
        selected_base = member.logical_type.value if isinstance(member.logical_type, NullableType) else member.logical_type
        if isinstance(selected_base, StructType):
            traversals.append(Traversal("struct", path))
        elif isinstance(selected_base, ArrayType):
            traversals.append(Traversal("array", path))
        result = field_reference(
            source=parent_model.source,
            path=path,
            logical_type=result_type,
            traversals=traversals,
            row_semantics=parent_model.row_semantics,
        )
    else:
        result = operation(
            "struct_field",
            parent_model,
            logical_type=result_type,
            parameters={"name": member.name},
        )
    from .factory import wrap_expression
    return select_expression(wrap_expression(result))


def _expansion_scope(model) -> tuple[str, ...]:
    if isinstance(model, FieldReferenceExpression):
        return (model.source, *model.path)
    if isinstance(model, OperationExpression) and model.operator == "struct_field":
        parent = model.arguments[0]
        if isinstance(parent, OperationExpression) and parent.operator == "expand":
            effects = parent.row_semantics.effects
            name = next((p.value for p in model.parameters if p.name == "name"), None)
            if effects and effects[-1].mode == "expand" and isinstance(name, str) and name:
                return (*effects[-1].scope, name)
    encoded = json.dumps(encode_expression(model), sort_keys=True, separators=(",", ":")).encode()
    return ("expression", sha256(encoded).hexdigest())


def _expand(expression: ValueExpression[Any], array_type: ArrayType) -> ValueSelection[Any]:
    from .factory import wrap_expression
    result = operation(
        "expand",
        expression.model,
        logical_type=array_type.item,
        row_semantics=RowSemantics("expand", _expansion_scope(expression.model)),
    )
    return select_expression(wrap_expression(result))


def select_expression[T](expression: ValueExpression[T]) -> ValueSelection[T]:
    """Wrap a bindable expression in the selection matching its logical shape."""
    logical_type = expression.logical_type
    if isinstance(logical_type, NullableType):
        return cast(ValueSelection[T], NullableSelection(expression))
    if isinstance(logical_type, ArrayType):
        return cast(ValueSelection[T], ArraySelection(expression))
    if isinstance(logical_type, StructType):
        return cast(ValueSelection[T], StructSelection(expression))
    return ValueSelection(expression)


def select_member(name: str, logical_type: LogicalType, declaration: StructType) -> ValueSelection[Any]:
    """Create the temporary selection returned by a field on a struct proxy."""
    member = _SelectedMember(name, logical_type, declaration)
    base = logical_type.value if isinstance(logical_type, NullableType) else logical_type
    if isinstance(logical_type, NullableType):
        return NullableSelection(member=member)
    if isinstance(base, ArrayType):
        return ArraySelection(member=member)
    if isinstance(base, StructType):
        return StructSelection(member=member)
    return ValueSelection(member=member)


# Imports are intentionally late: they exist for descriptor annotations and do
# not participate in selection behavior.
from .arrays import ArrayExpression
from .boolean import BoolExpression
from .custom import CustomDataTypeExpression
from .nullable import NullableExpression
from .numeric import FloatExpression, IntExpression
from .structs import StructExpression
from .text import StrExpression


__all__ = [
    "ArrayRowEffects", "ArraySelection", "NullableDataType", "NullableRowEffects",
    "NullableSelection", "RowEffects", "SelectionDataType", "SelectionStructured",
    "SelectionUnit", "StructSelection", "ValueInput", "ValueSelection",
    "as_expression", "select_expression", "select_member",
]
