"""The array selection: present-array value operations and row expansion."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from ...types.interfaces import Array, ArrayType, INT, Nullable, STR
from .._apply import apply_operation
from .._coercion import expression_input
from ..values import ValueExpression
from ._navigation import _expand, select_expression
from ._types import NullableDataType, SelectionUnit
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
        from ..arrays import _transform_items

        expression = self._require_expression()
        if not isinstance(self.logical_type, ArrayType):
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
        from ..arrays import _drop_null_items

        expression = self._require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("drop_null_items requires an array selection")
        return cast(
            "ArraySelection[Any]",
            select_expression(_drop_null_items(expression)),
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
        from ..arrays import _array_operation

        expression = self._require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("sort requires an array selection")
        return cast(
            "ArraySelection[TItem]",
            select_expression(_array_operation(expression, "sort")),
        )

    def distinct(self) -> "ArraySelection[TItem]":
        """Keep one copy of each item in the array.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.distinct().model.operator == "distinct"
            ```
        """
        from ..arrays import _array_operation

        expression = self._require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("distinct requires an array selection")
        return cast(
            "ArraySelection[TItem]",
            select_expression(_array_operation(expression, "distinct")),
        )

    def unique(self) -> "ArraySelection[TItem]":
        """Keep one copy per item; the selection spelling of ``distinct``.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.unique().model.operator == "distinct"
            ```
        """
        return self.distinct()

    def join(self, separator: str) -> ValueSelection[str]:
        """Join the array's non-null string items with ``separator``.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.join(", ").logical_type.name == "str"
            ```
        """
        expression = self._require_expression()
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("join requires an array selection")
        return select_expression(
            apply_operation(
                "join", expression, expression_input(separator, STR)
            )
        )

    def concat(self, separator: str) -> ValueSelection[str]:
        """Join non-null string items; the selection spelling of ``join``.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.concat(", ").logical_type.name == "str"
            ```
        """
        return self.join(separator)

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
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("at requires an array selection")
        result = apply_operation(
            "array_at",
            self._require_expression(),
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
        if not isinstance(self.logical_type, ArrayType):
            raise TypeError("slice requires an array selection")
        result = apply_operation(
            "array_slice",
            self._require_expression(),
            expression_input(start, INT),
            expression_input(end, INT),
        )
        return cast("ArraySelection[TItem]", select_expression(result))

    def alter_rows(self) -> "ArrayRowEffects[TItem]":
        """Opt in to the row-changing operations of this array selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field
            from kg_build_system.expressions import ArrayRowEffects

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert isinstance(Row.names.alter_rows(), ArrayRowEffects)
            ```
        """
        from .effects import ArrayRowEffects

        return ArrayRowEffects(self)

    @overload
    def expand[U: SelectionUnit](self: "ArraySelection[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "ArraySelection[Nullable[U]]") -> "NullableSelection[U]": ...
    @overload
    def expand[S: Any](self: "ArraySelection[S]") -> "StructSelection[S]": ...
    @overload
    def expand[S: Any](self: "ArraySelection[Nullable[S]]") -> "NullableSelection[S]": ...
    @overload
    def expand[I: NullableDataType](self: "ArraySelection[Array[I]]") -> "ArraySelection[I]": ...
    def expand(self) -> ValueSelection[Any]:
        """One row per array element.

        The item type determines the result; a nullable item keeps its own
        nullable selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            assert Row.names.expand().logical_type.name == "str"
            ```
        """
        logical_type = self.logical_type
        if not isinstance(logical_type, ArrayType):
            raise TypeError("expand requires an array selection")
        return _expand(self._require_expression())


__all__ = ["ArraySelection"]
