"""Author-facing selection families, row-effects handles and normalizers.

The classes are defined by their family module; this surface composes the names
an author writes and the helpers another framework package may use.

Example:
    ```python
    from kg_build_system import Field, Table, field
    from kg_build_system.expressions import ValueSelection

    class Row(Table):
        name: Field[str] = field(name="name")

    assert isinstance(Row.name, ValueSelection)
    ```
"""
from __future__ import annotations

from ._navigation import (
    as_expression, select_expression, select_member,
)
from ._types import (
    NullableDataType, SelectionDataType, SelectionStructured, SelectionUnit,
)
from .array import ArraySelection
from .effects import ArrayRowEffects, NullableRowEffects, RowEffects
from .nullable import NullableSelection
from .struct import StructSelection
from .value import ValueInput, ValueSelection


__all__ = [
    "ArrayRowEffects", "ArraySelection", "NullableDataType", "NullableRowEffects",
    "NullableSelection", "RowEffects", "SelectionDataType", "SelectionStructured",
    "SelectionUnit", "StructSelection", "ValueInput", "ValueSelection",
    "as_expression", "select_expression", "select_member",
]
