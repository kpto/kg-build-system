"""One-shot row-effect handles for selections."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from ...types.interfaces import Array, Nullable

if TYPE_CHECKING:
    from ..boolean import BoolExpression
    from .array import ArraySelection
    from .nullable import NullableSelection
    from ._types import NullableDataType, SelectionUnit
    from .value import ValueSelection


SSelection = TypeVar("SSelection", bound="ValueSelection[Any]")
TItem = TypeVar("TItem")


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

    def drop_null(self) -> SSelection:
        """A non-null selection has no null row; the old spelling is a no-op."""
        return self._selection

    def expand(self) -> SSelection:
        """Only array selections expand; the base spelling is refused at runtime."""
        raise TypeError("expand requires an array selection")

    def drop_if(self, predicate: Callable[[SSelection], "BoolExpression"]) -> SSelection:
        """Drop rows whose value does not satisfy the predicate."""
        return self._selection.drop_if(predicate)


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
        """One row per array element."""
        return cast("ArraySelection[Any]", self._selection).expand()


class NullableRowEffects(RowEffects["NullableSelection[TItem]"], Generic[TItem]):
    """Row effects available on a nullable selection."""

    @overload
    def drop_null[U: SelectionUnit](self: "NullableRowEffects[U]") -> "ValueSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def drop_null[I: NullableDataType](self: "NullableRowEffects[Array[I]]") -> "ArraySelection[I]": ...
    @overload
    def drop_null[S: Any](self: "NullableRowEffects[S]") -> Any: ...
    def drop_null(self):
        """Drop rows whose value is null."""
        return cast("NullableSelection[Any]", self._selection).drop_null()

    @overload
    def expand[U: SelectionUnit](self: "NullableRowEffects[Array[U]]") -> "ValueSelection[U]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def expand[U: SelectionUnit](self: "NullableRowEffects[Array[Nullable[U]]]") -> "NullableSelection[U]": ...
    @overload
    def expand[S: Any](self: "NullableRowEffects[Array[S]]") -> Any: ...
    @overload
    def expand[I: NullableDataType](self: "NullableRowEffects[Array[Array[I]]]") -> "ArraySelection[I]": ...
    def expand(self):
        """One row per element of a present array, yielding none when absent."""
        return cast("NullableSelection[Any]", self._selection).expand()


__all__ = ["ArrayRowEffects", "NullableRowEffects", "RowEffects"]
