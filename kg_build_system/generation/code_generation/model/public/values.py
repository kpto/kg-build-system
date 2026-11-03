"""Static values accepted by a generation request configuration."""
from __future__ import annotations

type StaticValue = (
    str | int | float | bool | None
    | list[StaticValue] | tuple[StaticValue, ...] | dict[str, StaticValue]
)

__all__ = ["StaticValue"]
