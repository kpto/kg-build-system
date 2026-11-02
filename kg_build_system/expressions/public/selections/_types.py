"""Author-facing type aliases for the selection surface.

Example:
    ```python
    from kg_build_system.expressions.selections import SelectionUnit

    assert SelectionUnit is not None
    ```
"""
from __future__ import annotations

from ....types.internal import (
    Array, CustomDataType, Date, Nullable, Struct, Time, Timestamp, Uuid,
)


type SelectionUnit = bool | int | float | str | Date | Time | Timestamp | Uuid | CustomDataType
type SelectionStructured = Array[NullableDataType] | Struct
type SelectionDataType = SelectionUnit | SelectionStructured
type NullableDataType = SelectionDataType | Nullable[SelectionDataType]


__all__ = [
    "NullableDataType", "SelectionDataType", "SelectionStructured", "SelectionUnit",
]
