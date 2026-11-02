"""Bindable array expression family."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from ..types.interfaces import (
    Array, ArrayType, Nullable, NullableType, STR, Struct, StructType,
)
from ._apply import apply_operation
from ._coercion import expression_input
from ._semantics import row_effects
from ._model import VariableExpression
from .values import ValueExpression

if TYPE_CHECKING:
    from .selections import (
        ArraySelection, NullableDataType, NullableSelection, SelectionDataType,
        SelectionUnit, StructSelection, ValueSelection,
    )
    from .text import StrExpression


TItem = TypeVar("TItem")


def _transform_items(
    expression: ValueExpression[Any],
    selector: Callable[[Any], ValueExpression[Any]],
) -> ValueExpression[Any]:
    """Apply one typed selector to every element of an array."""
    from ._visitors import walk_expression
    from .factory import wrap_expression
    from .selections import as_expression, select_expression

    logical_type = expression.logical_type
    array_nullable = isinstance(logical_type, NullableType)
    array_base = logical_type.value if array_nullable else logical_type
    if not isinstance(array_base, ArrayType):
        raise TypeError("transform_items requires an array expression")
    element = array_base.item
    element_nullable = isinstance(element, NullableType)
    element_base = element.value if element_nullable else element

    item_expression = wrap_expression(
        VariableExpression(name="item", logical_type=element_base)
    )
    proxy = (
        select_expression(item_expression)
        if isinstance(element_base, StructType)
        else item_expression
    )
    body = as_expression(selector(proxy))
    if any(row_effects(node.row_semantics) for node in walk_expression(body.model)):
        raise TypeError("transform_items selectors must not contain row effects")

    return apply_operation(
        "transform_items",
        expression.model,
        body.model,
        item="item",
    )


def _drop_null_items(expression: ValueExpression[Any]) -> ValueExpression[Any]:
    """Drop null items while keeping the array itself present or absent."""
    logical_type = expression.logical_type
    array_base = (
        logical_type.value if isinstance(logical_type, NullableType) else logical_type
    )
    if not isinstance(array_base, ArrayType):
        raise TypeError("drop_null_items requires an array expression")
    if not isinstance(array_base.item, NullableType):
        return expression
    return apply_operation("drop_null_items", expression.model)


def _array_operation(
    expression: ValueExpression[Any], operator: str,
) -> ValueExpression[Any]:
    return apply_operation(operator, expression.model)


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
