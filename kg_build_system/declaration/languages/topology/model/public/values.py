"""Graph value and property-slot types an author writes."""
from __future__ import annotations

from kg_build_system.declaration.foundations.expressions.model.public import (
    NullableAuthoringInput,
    ValueInput,
)
from kg_build_system.kernel.model.public.types import (
    Array, CustomDataType, Date, Time, Timestamp, Uuid,
)

type GraphScalar = (
    bool | int | float | str | Date | Time | Timestamp | Uuid | CustomDataType
)
# A graph property may also be a flat, homogeneous list of non-null scalars.
type GraphArray = Array[GraphScalar]
type GraphValue = GraphScalar | GraphArray | None
type NonNullableGraphValue = GraphScalar

# The public slot describes accepted authoring values; declaration metadata is
# a separate object returned by ``property()``.
type PropertySlot[T: GraphValue] = ValueInput[T] | NullableAuthoringInput[T]


__all__ = [
    "GraphArray", "GraphScalar", "GraphValue", "NonNullableGraphValue",
    "PropertySlot",
]
