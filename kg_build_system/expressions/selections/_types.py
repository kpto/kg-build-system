"""Author-facing type aliases for the selection surface."""
from __future__ import annotations

from ...types.interfaces import (
    Array, CustomDataType, Date, Nullable, Struct, Time, Timestamp, Uuid,
)


type SelectionUnit = bool | int | float | str | Date | Time | Timestamp | Uuid | CustomDataType
type SelectionStructured = Array[NullableDataType] | Struct
type SelectionDataType = SelectionUnit | SelectionStructured
type NullableDataType = SelectionDataType | Nullable[SelectionDataType]


__all__ = [
    "NullableDataType", "SelectionDataType", "SelectionStructured", "SelectionUnit",
]
