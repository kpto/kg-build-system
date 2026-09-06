"""Bindable array expression family."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from ..types import Array, ArrayType, Nullable, NullableType, STR, Struct
from ._coercion import expression_input
from .base import operation
from .values import ValueExpression

if TYPE_CHECKING:
    from .selections import (
        ArraySelection, NullableDataType, NullableSelection, SelectionDataType,
        SelectionUnit, ValueSelection,
    )
    from .text import StrExpression


TItem = TypeVar("TItem")


class ArrayExpression(ValueExpression[Array[TItem]], Generic[TItem]):
    def __init__(self, model) -> None:
        if not isinstance(model.logical_type, ArrayType):
            raise TypeError("ArrayExpression requires an array logical type")
        super().__init__(model)

    @overload
    def map_items[S: Struct, I: NullableDataType](
        self: "ArrayExpression[S]", selector: Callable[[S], ArraySelection[I]],
    ) -> "ArrayExpression[Array[I]]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def map_items[S: Struct, Inner: Struct](
        self: "ArrayExpression[S]", selector: Callable[[S], ValueSelection[Inner]],
    ) -> "ArrayExpression[Inner]": ...
    @overload
    def map_items[S: Struct, D: SelectionDataType](
        self: "ArrayExpression[S]", selector: Callable[[S], NullableSelection[D]],
    ) -> "ArrayExpression[Nullable[D]]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def map_items[S: Struct, U: SelectionUnit](
        self: "ArrayExpression[S]", selector: Callable[[S], ValueSelection[U]],
    ) -> "ArrayExpression[U]": ...
    @overload
    def map_items[S: Struct, I: NullableDataType](
        self: "ArrayExpression[Nullable[S]]", selector: Callable[[S], ArraySelection[I]],
    ) -> "ArrayExpression[Nullable[Array[I]]]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def map_items[S: Struct, Inner: Struct](
        self: "ArrayExpression[Nullable[S]]", selector: Callable[[S], ValueSelection[Inner]],
    ) -> "ArrayExpression[Nullable[Inner]]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def map_items[S: Struct, D: SelectionDataType](
        self: "ArrayExpression[Nullable[S]]", selector: Callable[[S], NullableSelection[D]],
    ) -> "ArrayExpression[Nullable[D]]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def map_items[S: Struct, U: SelectionUnit](
        self: "ArrayExpression[Nullable[S]]", selector: Callable[[S], ValueSelection[U]],
    ) -> "ArrayExpression[Nullable[U]]": ...  # pyright: ignore[reportInvalidTypeArguments]
    def map_items(self, selector: Callable[[Any], ValueSelection[Any]]) -> "ArrayExpression[Any]":
        """Project one struct member out of every element: ``Array[S]`` to ``Array[member]``."""
        from .selections import _map_items

        return _map_items(self, selector)  # type: ignore[return-value]

    @overload
    def without_nulls[I](self: "ArrayExpression[Nullable[I]]") -> "ArrayExpression[I]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def without_nulls(self: "ArrayExpression[TItem]") -> "ArrayExpression[TItem]": ...
    def without_nulls(self) -> "ArrayExpression[Any]":
        """Drop null items, keeping the array itself: ``Array[T | None]`` to ``Array[T]``.

        A graph property array must hold non-null items, and no target stores
        null array items faithfully, so the conversion is explicit here.
        A null item is an absent value inside a present list; this operation
        states that it is dropped. An already non-null item type returns this
        expression unchanged.
        """
        logical_type = self.logical_type
        assert isinstance(logical_type, ArrayType)
        item = logical_type.item
        if not isinstance(item, NullableType):
            return self
        return ArrayExpression(
            operation(
                "without_nulls", self.model,
                logical_type=ArrayType(item.value),
            )
        )

    def sorted(self) -> "ArrayExpression[TItem]":
        """A copy of the array with its items in ascending order.

        Sorting makes an array's content independent of the order the source
        listed it in, so a key built from the items names the same record no
        matter how the source ordered it. A null array stays a null array.
        """
        return ArrayExpression(
            operation("sorted", self.model, logical_type=self.logical_type)
        )

    def distinct(self) -> "ArrayExpression[TItem]":
        """A copy of the array with each item kept once.

        Projection of a repeated nested member into a set-valued property:
        the same event named by three liabilities of one record is one item.
        Combine with :meth:`sorted` for a deterministic array. A null array
        stays a null array.
        """
        return ArrayExpression(
            operation("distinct", self.model, logical_type=self.logical_type)
        )

    def join(self, separator: str) -> "StrExpression":
        """Concatenate the items with ``separator``: ``Array[str]`` to ``str``.

        The items must be non-null strings; a null array joins to a null
        string. Use :meth:`without_nulls` first when the source carries null
        items.
        """
        from .text import StrExpression

        logical_type = self.logical_type
        assert isinstance(logical_type, ArrayType)
        if logical_type.item != STR:
            raise TypeError("join requires an array of non-null strings")
        return StrExpression(
            operation(
                "join", self.model, expression_input(separator, STR),
                logical_type=STR,
            )
        )


__all__ = ["ArrayExpression"]
