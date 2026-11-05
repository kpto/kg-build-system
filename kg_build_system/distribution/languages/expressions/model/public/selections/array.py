"""The array selection: present-array value operations and row expansion.

Example:
    ```python
    from kg_build_system import Field, Table, field
    from kg_build_system import Array

    class Row(Table):
        tags: Field[Array[str]] = field(name="tags")

    assert Row.tags.alter_rows().expand() is not None
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from kg_build_system.kernel.model.public.types import Array, ArrayType, INT, Nullable, STR
from ..values import ValueExpression
from .types import NullableDataType, SelectionUnit
from .value import ValueInput, ValueSelection

if TYPE_CHECKING:
    from .effects import ArrayRowEffects
    from .nullable import NullableSelection
    from .struct import StructSelection


TItem = TypeVar("TItem")


class ArraySelection(ValueSelection[Array[TItem]], Generic[TItem]):
    """Array selection supporting explicit row-producing expansion."""

    @overload
    def transform_items[S: Any, U](
        self: "ArraySelection[S]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "ArraySelection[U]": ...
    @overload
    def transform_items[U](
        self: "ArraySelection[TItem]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "ArraySelection[U]": ...
    @overload
    def transform_items[S: Any, U](
        self: "ArraySelection[Nullable[S]]",
        selector: Callable[[StructSelection[S]], ValueExpression[U]],
    ) -> "ArraySelection[Nullable[U]]": ...
    @overload
    def transform_items[U](
        self: "ArraySelection[Nullable[TItem]]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "ArraySelection[Nullable[U]]": ...
    def transform_items(self, selector: Callable[[Any], ValueExpression[Any]]) -> "ArraySelection[Any]":
        """Apply a selector to every item, preserving the array's item count.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            selected = Row.names.transform_items(lambda item: item.append("!"))
            assert selected.model.operator == "transform_items"
            ```
        """
        from ....service._private.arrays import _transform_items as transform_items
        from ....service._private.selections import select_expression

        expression = self.require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("transform_items requires an array selection")
        return cast(
            "ArraySelection[Any]",
            select_expression(transform_items(expression, selector)),
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
        """Remove null items from a nullable item array.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str | None]] = field(name="names")

            selected = Row.names.drop_null_items()
            assert selected.model.operator == "drop_null_items"
            ```
        """
        from ....service._private.arrays import _drop_null_items as drop_null_items
        from ....service._private.selections import select_expression

        expression = self.require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("drop_null_items requires an array selection")
        return cast(
            "ArraySelection[Any]",
            select_expression(drop_null_items(expression)),
        )

    def sort(self) -> "ArraySelection[TItem]":
        """Sort the items of the array in ascending order.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.sort().model.operator == "sort"
            ```
        """
        from ....service._private.arrays import _array_operation as array_operation
        from ....service._private.selections import select_expression

        expression = self.require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("sort requires an array selection")
        return cast(
            "ArraySelection[TItem]",
            select_expression(array_operation(expression, "sort")),
        )

    def unique(self) -> "ArraySelection[TItem]":
        """Keep one copy of each item in the array.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.unique().model.operator == "distinct"
            ```
        """
        from ....service._private.arrays import _array_operation as array_operation
        from ....service._private.selections import select_expression

        expression = self.require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("unique requires an array selection")
        return cast(
            "ArraySelection[TItem]",
            select_expression(array_operation(expression, "distinct")),
        )

    def concat(self, separator: str) -> ValueSelection[str]:
        """Join the array's non-null string items with ``separator``.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.concat(", ").logical_type.name == "str"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import select_expression

        expression = self.require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("concat requires an array selection")
        return select_expression(
            apply_operation(
                "join", expression, expression_input(separator, STR)
            )
        )

    @overload
    def at[U: SelectionUnit](self: "ArraySelection[U]", index: int | ValueInput[int]) -> "NullableSelection[U]": ...
    @overload
    def at[U: SelectionUnit](self: "ArraySelection[Nullable[U]]", index: int | ValueInput[int]) -> "NullableSelection[U]": ...
    @overload
    def at[S: Any](self: "ArraySelection[S]", index: int | ValueInput[int]) -> "NullableSelection[S]": ...
    @overload
    def at[I: NullableDataType](self: "ArraySelection[Array[I]]", index: int | ValueInput[int]) -> "NullableSelection[Array[I]]": ...
    def at(self, index: int | ValueInput[int]) -> ValueSelection[Any]:
        """The nullable item at a 0-based index.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            selected = Row.names.at(0)
            assert selected.logical_type.value.name == "str"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import select_expression

        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("at requires an array selection")
        result = apply_operation(
            "array_at",
            self.require_expression(),
            expression_input(index, INT),
        )
        return select_expression(result)

    def slice(self, start: int | ValueInput[int], end: int | ValueInput[int]) -> "ArraySelection[TItem]":
        """The array between a 0-based start and an end-exclusive end.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.slice(0, 1).model.operator == "array_slice"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import select_expression

        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("slice requires an array selection")
        result = apply_operation(
            "array_slice",
            self.require_expression(),
            expression_input(start, INT),
            expression_input(end, INT),
        )
        return cast("ArraySelection[TItem]", select_expression(result))

    def alter_rows(self) -> "ArrayRowEffects[TItem]":
        """Opt in to the row-changing operations of this array selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field
            from kg_build_system.distribution.languages.expressions.model.public import ArrayRowEffects

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert isinstance(Row.names.alter_rows(), ArrayRowEffects)
            ```
        """
        from .effects import ArrayRowEffects

        return ArrayRowEffects(self)


__all__ = ["ArraySelection"]
