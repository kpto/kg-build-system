"""The struct selection: declared-member navigation with ``extract``.

Example:
    ```python
    from kg_build_system import Field, Struct, Table, field

    class Detail(Struct):
        label: Field[str] = field(name="label")

    class Row(Table):
        detail: Field[Detail] = field(name="detail")

    assert Row.detail is not None
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from ....types.internal import Struct, StructType
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
        """Read one declared member of this struct.

        The selector receives a type-level proxy of the declaration, so only
        declared fields can be selected. A nullable member yields a nullable
        selection.

        Example:
            ```python
            from kg_build_system import Field, Struct, Table, field

            class Detail(Struct):
                label: Field[str] = field(name="label")

            class Row(Table):
                detail: Field[Detail] = field(name="detail")

            selected = Row.detail.extract(lambda detail: detail.label)
            assert selected.logical_type.name == "str"
            ```
        """
        logical_type = self.logical_type
        if not isinstance(logical_type, StructType):
            raise TypeError("extract requires a struct selection")
        return _pick(self, selector, logical_type, propagate_null=False)

    def pick(self, selector: Callable[[TStruct], ValueSelection[Any]]) -> ValueSelection[Any]:
        """Legacy spelling of ``extract``.

        Example:
            ```python
            from kg_build_system import Field, Struct, Table, field

            class Detail(Struct):
                label: Field[str] = field(name="label")

            class Row(Table):
                detail: Field[Detail] = field(name="detail")

            selected = Row.detail.pick(lambda detail: detail.label)
            assert selected.logical_type.name == "str"
            ```
        """
        return self.extract(selector)


__all__ = ["StructSelection"]
