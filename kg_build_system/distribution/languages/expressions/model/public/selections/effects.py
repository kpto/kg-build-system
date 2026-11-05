"""One-shot row-effect handles for selections.

Example:
    ```python
    from kg_build_system import Array, Field, Table, field

    class Row(Table):
        tags: Field[Array[str]] = field(name="tags")

    assert Row.tags.alter_rows().expand() is not None
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from kg_build_system.kernel.model.public.types import Array, Nullable

if TYPE_CHECKING:
    from ..boolean import BoolExpression
    from .array import ArraySelection
    from .nullable import NullableSelection
    from .types import NullableDataType, SelectionUnit
    from .value import ValueSelection


SSelection = TypeVar("SSelection", bound="ValueSelection[Any]")
TItem = TypeVar("TItem")


class RowEffects(Generic[SSelection]):
    """A one-shot opt-in to the row-changing operations of one selection.

    Every method consumes the permission: it returns a selection, not another
    handle, so a second row effect must opt in again.
    """

    __slots__ = ("_selection", "_used")

    def __init__(self, selection: SSelection) -> None:
        self._selection = selection
        self._used = False

    def drop_null(self) -> SSelection:
        """A present selection has no null row, so this is a no-op.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selection = Row.name
            assert selection.alter_rows().drop_null() is selection
            ```
        """
        if self._used:
            raise RuntimeError(
                "a row-effect handle is one-shot; call alter_rows() again"
            )
        self._used = True
        return self._selection

    def drop_if(self, predicate: Callable[[SSelection], "BoolExpression"]) -> SSelection:
        """Drop rows whose value does not satisfy the predicate.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selected = Row.name.alter_rows().drop_if(
                lambda name: name.expression.equals("Depot")
            )
            assert selected.model.operator == "drop_if"
            ```
        """
        from ....service._private.selections import drop_if_selection

        if self._used:
            raise RuntimeError(
                "a row-effect handle is one-shot; call alter_rows() again"
            )
        self._used = True
        return cast(SSelection, drop_if_selection(self._selection, predicate))


class ArrayRowEffects(RowEffects["ArraySelection[TItem]"], Generic[TItem]):
    """Row effects available on an array selection."""

    @overload
    def expand[U: SelectionUnit](self: "ArrayRowEffects[U]") -> "ValueSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "ArrayRowEffects[Nullable[U]]") -> "NullableSelection[U]": ...
    @overload
    def expand[S: Any](self: "ArrayRowEffects[S]") -> Any: ...
    @overload
    def expand[I: NullableDataType](self: "ArrayRowEffects[Array[I]]") -> "ArraySelection[I]": ...
    def expand(self):
        """One row per array element.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str]] = field(name="names")

            selected = Row.names.alter_rows().expand()
            assert selected.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import expand_selection

        if self._used:
            raise RuntimeError(
                "a row-effect handle is one-shot; call alter_rows() again"
            )
        self._used = True
        return expand_selection(self._selection)


class NullableRowEffects(RowEffects["NullableSelection[TItem]"], Generic[TItem]):
    """Row effects available on a nullable selection."""

    @overload
    def drop_null[U: SelectionUnit](self: "NullableRowEffects[U]") -> "ValueSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def drop_null[I: NullableDataType](self: "NullableRowEffects[Array[I]]") -> "ArraySelection[I]": ...
    @overload
    def drop_null[S: Any](self: "NullableRowEffects[S]") -> Any: ...
    def drop_null(self) -> Any:
        """Drop rows whose value is null.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            selected = Row.name.alter_rows().drop_null()
            assert selected.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import drop_null_selection

        if self._used:
            raise RuntimeError(
                "a row-effect handle is one-shot; call alter_rows() again"
            )
        self._used = True
        return cast(
            "NullableSelection[Any]", drop_null_selection(self._selection),
        )


class NullableArrayRowEffects(
    NullableRowEffects[Array[TItem]], Generic[TItem],
):
    """Row effects available on a nullable array selection."""

    @overload
    def expand[U: SelectionUnit](self: "NullableArrayRowEffects[U]") -> "ValueSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "NullableArrayRowEffects[Nullable[U]]") -> "NullableSelection[U]": ...
    @overload
    def expand[S: Any](self: "NullableArrayRowEffects[S]") -> Any: ...
    @overload
    def expand[I: NullableDataType](self: "NullableArrayRowEffects[Array[I]]") -> "ArraySelection[I]": ...
    def expand(self):
        """One row per element of a present array, yielding none when absent.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                names: Field[Array[str] | None] = field(name="names")

            selected = Row.names.alter_rows().expand()
            assert selected.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import expand_selection

        if self._used:
            raise RuntimeError(
                "a row-effect handle is one-shot; call alter_rows() again"
            )
        self._used = True
        return expand_selection(self._selection)


__all__ = [
    "ArrayRowEffects", "NullableArrayRowEffects", "NullableRowEffects",
    "RowEffects",
]
