"""The struct selection: declared-member navigation with ``extract``."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from ...types.interfaces import Struct, StructType
from ._navigation import _pick
from ._types import NullableDataType, SelectionDataType, SelectionUnit
from .value import ValueSelection

if TYPE_CHECKING:
    from .array import ArraySelection
    from .nullable import NullableSelection


TStruct = TypeVar("TStruct", bound=Struct)


class StructSelection(ValueSelection[TStruct], Generic[TStruct]):
    """Struct selection supporting declared-member navigation."""

    @overload
    def extract[I: NullableDataType](self, selector: Callable[[TStruct], "ArraySelection[I]"]) -> "ArraySelection[I]": ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def extract[Inner: Struct](self, selector: Callable[[TStruct], "StructSelection[Inner]"]) -> "StructSelection[Inner]": ...
    @overload
    def extract[D: SelectionDataType](self, selector: Callable[[TStruct], "NullableSelection[D]"]) -> "NullableSelection[D]": ...
    @overload
    def extract[U: SelectionUnit](self, selector: Callable[[TStruct], ValueSelection[U]]) -> ValueSelection[U]: ...
    def extract(self, selector: Callable[[TStruct], ValueSelection[Any]]) -> ValueSelection[Any]:
        logical_type = self.logical_type
        if not isinstance(logical_type, StructType):
            raise TypeError("extract requires a struct selection")
        return _pick(self, selector, logical_type, propagate_null=False)

    def pick(self, selector: Callable[[TStruct], ValueSelection[Any]]) -> ValueSelection[Any]:
        """Legacy spelling of ``extract``."""
        return self.extract(selector)


__all__ = ["StructSelection"]
