"""Bindable array expression family.

Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.types import ArrayType, INT

    numbers = value_expression([2, 1], logical_type=ArrayType(INT))
    assert numbers.sort().model.operator == "sort"
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from ......kernel.internal.types import Array, ArrayType, Nullable, STR, Struct, StructType
from ..._private.apply import apply_operation
from ..._private.arrays import _array_operation, _drop_null_items, _transform_items
from ..._private.coercion import expression_input
from .values import ValueExpression

if TYPE_CHECKING:
    from .selections import ArraySelection, NullableDataType, NullableSelection, SelectionDataType, SelectionUnit, StructSelection, ValueSelection
    from .text import StrExpression


TItem = TypeVar("TItem")


class ArrayExpression(ValueExpression[Array[TItem]], Generic[TItem]):
    def __init__(self, model) -> None:
        if not isinstance(model.logical_type, ArrayType):
            raise TypeError("ArrayExpression requires an array logical type")
        super().__init__(model)

    @overload
    def transform_items[S: Struct, U](
        self: "ArrayExpression[S]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "ArrayExpression[U]": ...
    @overload
    def transform_items[U](
        self: "ArrayExpression[TItem]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "ArrayExpression[U]": ...
    @overload
    def transform_items[S: Struct, U](
        self: "ArrayExpression[Nullable[S]]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "ArrayExpression[Nullable[U]]": ...
    @overload
    def transform_items[U](
        self: "ArrayExpression[Nullable[TItem]]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "ArrayExpression[Nullable[U]]": ...
    def transform_items(
        self, selector: Callable[[Any], ValueExpression[Any]],
    ) -> "ArrayExpression[Any]":
        """Apply one explicit expression to every item, without expanding rows.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.types import ArrayType, INT

            numbers = value_expression([1, 2], logical_type=ArrayType(INT))
            selected = numbers.transform_items(lambda item: item.add(1))
            assert selected.model.operator == "transform_items"
            ```
        """
        return cast("ArrayExpression[Any]", _transform_items(self, selector))

    @overload
    def drop_null_items[I](self: "ArrayExpression[Nullable[I]]") -> "ArrayExpression[I]": ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def drop_null_items(self: "ArrayExpression[TItem]") -> "ArrayExpression[TItem]": ...
    def drop_null_items(self) -> "ArrayExpression[Any]":
        """Drop null items; a null array stays null and non-null items pass through.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.types import ArrayType, INT, NullableType

            values = value_expression(
                [1, None], logical_type=ArrayType(NullableType(INT))
            )
            assert values.drop_null_items().model.operator == "drop_null_items"
            ```
        """
        return cast("ArrayExpression[Any]", _drop_null_items(self))

    def sort(self) -> "ArrayExpression[TItem]":
        """Order the items ascending; a null array stays null.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.types import ArrayType, INT

            numbers = value_expression([2, 1], logical_type=ArrayType(INT))
            assert numbers.sort().model.operator == "sort"
            ```
        """
        return cast("ArrayExpression[TItem]", _array_operation(self, "sort"))

    def distinct(self) -> "ArrayExpression[TItem]":
        """Keep one copy per item; a null array stays null.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.types import ArrayType, INT

            numbers = value_expression([1, 1], logical_type=ArrayType(INT))
            assert numbers.distinct().model.operator == "distinct"
            ```
        """
        return cast("ArrayExpression[TItem]", _array_operation(self, "distinct"))

    def join(self, separator: str) -> "StrExpression":
        """Concatenate non-null string items with ``separator``.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.types import ArrayType, STR

            names = value_expression(["a", "b"], logical_type=ArrayType(STR))
            assert names.join(", ").model.operator == "join"
            ```
        """
        from .text import StrExpression

        logical_type = self.logical_type
        assert isinstance(logical_type, ArrayType)
        if logical_type.item != STR:
            raise TypeError("join requires an array of non-null strings")
        return StrExpression(
            apply_operation(
                "join", self.model, expression_input(separator, STR)
            ).model
        )


__all__ = ["ArrayExpression"]
