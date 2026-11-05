"""The nullable selection: null policy and nullable navigation.

Example:
    ```python
    from kg_build_system import Field, Table, field

    class Row(Table):
        name: Field[str | None] = field(name="name")

    assert Row.name.expression.append("!").model.operator == "concat"
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from kg_build_system.kernel.model.public.types import Array, ArrayType, INT, Nullable, NullableType, STR, Struct, StructType
from ..values import NullableAuthoringInput, ValueExpression
from .types import NullableDataType, SelectionDataType, SelectionUnit
from .value import ValueInput, ValueSelection

if TYPE_CHECKING:
    from .array import ArraySelection
    from .effects import NullableArrayRowEffects, NullableRowEffects
    from .struct import StructSelection


TItem = TypeVar("TItem")


class NullableSelection(
    ValueSelection[Nullable[TItem]],
    NullableAuthoringInput[TItem | None],
    Generic[TItem],
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
        """Replace a null value with a fallback while keeping the row.

        The fallback must have the nullable value's own logical type. The
        result is present; nullness is not propagated to it.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.default_to("unknown").logical_type.name == "str"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import as_expression, select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType):
            raise TypeError("default_to requires a nullable selection")
        normalized = (
            as_expression(value)
            if isinstance(value, (ValueSelection, ValueExpression))
            else value
        )
        fallback = expression_input(normalized, logical_type.value)
        result = apply_operation(
            "coalesce", self.require_expression(), fallback
        )
        return select_expression(result)

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
        """Read one declared member of this nullable struct.

        Example:
            ```python
            from kg_build_system import Field, Struct, Table, field

            class Detail(Struct):
                label: Field[str] = field(name="label")

            class Row(Table):
                detail: Field[Detail | None] = field(name="detail")

            selected = Row.detail.extract(lambda detail: detail.label)
            assert selected.logical_type.value.name == "str"
            ```
        """
        logical_type = self.logical_type
        from ....service._private.selections import _extract_member as extract_member

        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, StructType
        ):
            raise TypeError("extract requires a nullable struct selection")
        return extract_member(self, selector, logical_type.value, propagate_null=True)

    # Nullable-array operations preserve the array's own presence and return a
    # nullable selection; narrow with ``alter_rows().drop_null()`` first when
    # the result must be present.
    @overload
    def transform_items[S: Struct, U](
        self: "NullableSelection[Array[S]]",
        selector: Callable[[Any], ValueExpression[U]],
    ) -> "NullableSelection[Array[U]]": ...
    @overload
    def transform_items[U](
        self: "NullableSelection[Array[TItem]]",
        selector: Callable[[ValueExpression[TItem]], ValueExpression[U]],
    ) -> "NullableSelection[Array[U]]": ...
    def transform_items(self, selector: Callable[[Any], ValueExpression[Any]]) -> "NullableSelection[Any]":
        """Apply a selector to every item, keeping the array's own presence.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            selected = Row.names.transform_items(lambda item: item.append("!"))
            assert selected.model.operator == "transform_items"
            ```
        """
        from ....service._private.arrays import _transform_items as transform_items
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("transform_items requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(transform_items(self.require_expression(), selector)),
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
        """Remove null items, keeping the array's own presence.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str | None] | None] = field(name="names")

            selected = Row.names.drop_null_items()
            assert selected.model.operator == "drop_null_items"
            ```
        """
        from ....service._private.arrays import _drop_null_items as drop_null_items
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("drop_null_items requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(drop_null_items(self.require_expression())),
        )

    def sort(self) -> "NullableSelection[Any]":
        """Sort the items of a present array in ascending order.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert Row.names.sort().model.operator == "sort"
            ```
        """
        from ....service._private.arrays import _array_operation as array_operation
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("sort requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(array_operation(self.require_expression(), "sort")),
        )

    def unique(self) -> "NullableSelection[Any]":
        """Keep one copy of each item of a present array.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert Row.names.unique().model.operator == "distinct"
            ```
        """
        from ....service._private.arrays import _array_operation as array_operation
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("unique requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(
                array_operation(self.require_expression(), "distinct")
            ),
        )

    def concat(self, separator: str) -> "NullableSelection[str]":
        """Join non-null string items with ``separator``.

        Requires an array of non-null strings. The result is null when the
        array is null.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            joined = Row.names.concat(", ")
            assert joined.logical_type.value.name == "str"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("concat requires a nullable array selection")
        result = apply_operation(
            "join", self.require_expression(), expression_input(separator, STR)
        )
        return cast("NullableSelection[str]", select_expression(result))

    def at(self, index: int | ValueInput[int]) -> ValueSelection[Any]:
        """The nullable item at a 0-based index.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            selected = Row.names.at(0)
            assert selected.logical_type.value.name == "str"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("at requires a nullable array selection")
        return select_expression(
            apply_operation(
                "array_at",
                self.require_expression(),
                expression_input(index, INT),
            )
        )

    def slice(
        self, start: int | ValueInput[int], end: int | ValueInput[int],
    ) -> "NullableSelection[Any]":
        """The nullable array between a 0-based start and an end-exclusive end.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert Row.names.slice(0, 1).model.operator == "array_slice"
            ```
        """
        from ....service._private.apply import apply_operation
        from ....service._private.coercion import expression_input
        from ....service._private.selections import select_expression

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("slice requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(
                apply_operation(
                    "array_slice",
                    self.require_expression(),
                    expression_input(start, INT),
                    expression_input(end, INT),
                )
            ),
        )

    @overload
    def alter_rows[I: NullableDataType](
        self: "NullableSelection[Array[I]]",
    ) -> "NullableArrayRowEffects[I]": ...
    @overload
    def alter_rows(self) -> "NullableRowEffects[TItem]": ...
    def alter_rows(self) -> "NullableRowEffects[Any]":
        """Opt in to the row-changing operations of this nullable selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field
            from kg_build_system.distribution.languages.expressions.model.public import NullableRowEffects

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert isinstance(Row.names.alter_rows(), NullableRowEffects)
            ```
        """
        from .effects import NullableArrayRowEffects, NullableRowEffects

        logical_type = self.logical_type
        if isinstance(logical_type, NullableType) and isinstance(
            logical_type.value, ArrayType
        ):
            return NullableArrayRowEffects(cast(Any, self))
        return NullableRowEffects(self)


__all__ = ["NullableSelection"]
