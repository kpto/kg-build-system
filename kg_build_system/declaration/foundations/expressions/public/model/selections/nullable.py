"""The nullable selection: null policy, nullable navigation and legacy aliases.

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

from .......kernel.internal.types import Array, ArrayType, INT, Nullable, NullableType, STR, Struct, StructType
from ...._private.apply import apply_operation
from ...._private.coercion import expression_input
from ..values import NullableAuthoringInput, ValueExpression
from ...._private.selections import _expand, _pick, as_expression, select_expression
from ._types import NullableDataType, SelectionDataType, SelectionUnit
from .value import ValueInput, ValueSelection

if TYPE_CHECKING:
    from .array import ArraySelection
    from .effects import NullableRowEffects
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
            "coalesce", self._require_expression(), fallback
        )
        return select_expression(result)

    @overload
    def where_present[U: SelectionUnit](self: "NullableSelection[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def where_present[I: NullableDataType](self: "NullableSelection[Array[I]]") -> "ArraySelection[I]": ...
    @overload
    def where_present[S: Struct](self: "NullableSelection[S]") -> "StructSelection[S]": ...
    def where_present(self) -> ValueSelection[Any]:
        """Legacy spelling of the presence filter; see ``alter_rows().drop_null()``.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.where_present().logical_type.name == "str"
            ```
        """
        return self._drop_null()

    def _drop_null(self) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType):
            raise TypeError("where_present requires a nullable selection")
        return select_expression(
            apply_operation("where_present", self._require_expression())
        )

    @overload
    def drop_null[U: SelectionUnit](self: "NullableSelection[U]") -> ValueSelection[U]: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def drop_null[I: NullableDataType](self: "NullableSelection[Array[I]]") -> "ArraySelection[I]": ...
    @overload
    def drop_null[S: Struct](self: "NullableSelection[S]") -> "StructSelection[S]": ...
    def drop_null(self) -> ValueSelection[Any]:
        """Drop the row when this value is null.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.drop_null().logical_type.name == "str"
            ```
        """
        return self._drop_null()

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
        """One row per element of a present array; an absent array yields none.

        The item type determines the result; a nullable item keeps its own
        nullable selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert Row.names.expand().logical_type.name == "str"
            ```
        """
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("expand requires a nullable array selection")
        return _expand(self._require_expression())

    @overload
    def pick[S: Struct, U: SelectionUnit](
        self: "NullableSelection[S]", selector: Callable[[S], ValueSelection[U]],
    ) -> "NullableSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def pick[S: Struct, D: SelectionDataType](
        self: "NullableSelection[S]", selector: Callable[[S], "NullableSelection[D]"],
    ) -> "NullableSelection[D]": ...
    @overload
    def pick[S: Struct, I: NullableDataType](
        self: "NullableSelection[S]", selector: Callable[[S], "ArraySelection[I]"],
    ) -> "NullableSelection[Array[I]]": ...
    @overload
    def pick[S: Struct, Inner: Struct](
        self: "NullableSelection[S]", selector: Callable[[S], "StructSelection[Inner]"],
    ) -> "NullableSelection[Inner]": ...
    def pick(self, selector: Callable[[Any], ValueSelection[Any]]) -> ValueSelection[Any]:
        """Read one declared member of this nullable struct.

        The legacy spelling of ``extract``. The member inherits the parent
        struct's nullness.

        Example:
            ```python
            from kg_build_system import Field, Struct, Table, field

            class Detail(Struct):
                label: Field[str] = field(name="label")

            class Row(Table):
                detail: Field[Detail | None] = field(name="detail")

            selected = Row.detail.pick(lambda detail: detail.label)
            assert selected.logical_type.value.name == "str"
            ```
        """
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, StructType
        ):
            raise TypeError("pick requires a nullable struct selection")
        return _pick(self, selector, logical_type.value, propagate_null=True)

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
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, StructType
        ):
            raise TypeError("extract requires a nullable struct selection")
        return _pick(self, selector, logical_type.value, propagate_null=True)

    # Legacy nullable-array operations. They preserve the array's own presence
    # and return a nullable selection; narrow with ``where_present`` first when
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
        from ...._private.arrays import _transform_items

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
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
        from ...._private.arrays import _drop_null_items

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("drop_null_items requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(_drop_null_items(self._require_expression())),
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
        from ...._private.arrays import _array_operation

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("sort requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(_array_operation(self._require_expression(), "sort")),
        )

    def distinct(self) -> "NullableSelection[Any]":
        """Keep one copy of each item of a present array.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert Row.names.distinct().model.operator == "distinct"
            ```
        """
        from ...._private.arrays import _array_operation

        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("distinct requires a nullable array selection")
        return cast(
            "NullableSelection[Any]",
            select_expression(
                _array_operation(self._require_expression(), "distinct")
            ),
        )

    def unique(self) -> "NullableSelection[Any]":
        """Keep one copy per item; the legacy spelling of ``distinct``.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert Row.names.unique().model.operator == "distinct"
            ```
        """
        return self.distinct()

    def join(self, separator: str) -> "NullableSelection[str]":
        """Join non-null string items with ``separator``.

        Requires an array of non-null strings. The result is null when the
        array is null.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            joined = Row.names.join(", ")
            assert joined.logical_type.value.name == "str"
            ```
        """
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("join requires a nullable array selection")
        if logical_type.value.item != STR:
            raise TypeError("join requires an array of non-null strings")
        result = apply_operation(
            "join", self._require_expression(), expression_input(separator, STR)
        )
        return cast("NullableSelection[str]", select_expression(result))

    def concat(self, separator: str) -> "NullableSelection[str]":
        """Join non-null string items; the legacy spelling of ``join``.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            joined = Row.names.concat(", ")
            assert joined.logical_type.value.name == "str"
            ```
        """
        return self.join(separator)

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
        logical_type = self.logical_type
        if not isinstance(logical_type, NullableType) or not isinstance(
            logical_type.value, ArrayType
        ):
            raise TypeError("at requires a nullable array selection")
        return select_expression(
            apply_operation(
                "array_at",
                self._require_expression(),
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
                    self._require_expression(),
                    expression_input(start, INT),
                    expression_input(end, INT),
                )
            ),
        )

    def alter_rows(self) -> "NullableRowEffects[TItem]":
        """Opt in to the row-changing operations of this nullable selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field
            from kg_build_system.declaration.foundations.expressions.public import NullableRowEffects

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            assert isinstance(Row.names.alter_rows(), NullableRowEffects)
            ```
        """
        from .effects import NullableRowEffects

        return NullableRowEffects(self)


__all__ = ["NullableSelection"]
