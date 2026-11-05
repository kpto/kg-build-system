"""Internal declared-member metadata used by selection navigation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg_build_system.kernel.model.public.types import LogicalType, StructType


@dataclass(frozen=True, slots=True)
class SelectedMember:
    """One declared member read through a symbolic struct proxy.

    ``logical_type`` is the access type: a source member is already nullable
    and a computed member carries the type of its expression.
    """

    name: str
    logical_type: LogicalType
    declaration: StructType


__all__ = ["RowEffectHandle", "SelectedMember"]


class RowEffectHandle:
    """One-shot permission to apply a single row effect to a selection."""

    __slots__ = ("_consumed", "_selection")

    def __init__(self, selection: Any) -> None:
        self._selection = selection
        self._consumed = False

    def consume(self) -> Any:
        """Return the handled selection once, then refuse reuse."""
        if self._consumed:
            raise TypeError(
                "row-effect handle already consumed; call alter_rows() again"
            )
        self._consumed = True
        return self._selection
