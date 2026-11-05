"""Composition of DuckDB row-source emitters, keyed by plan node type."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from .distinct import DistinctEmitter
from .filter import FilterEmitter
from .group_by import GroupByEmitter
from .join import JoinEmitter
from .order_by import OrderByEmitter
from .scan import ScanEmitter
from .union import UnionEmitter
from .unnest import UnnestEmitter

if TYPE_CHECKING:
    from ..protocols import RowSourceEmitter

FAMILIES = (
    ScanEmitter(),
    FilterEmitter(),
    UnionEmitter(),
    DistinctEmitter(),
    OrderByEmitter(),
    JoinEmitter(),
    GroupByEmitter(),
    UnnestEmitter(),
)


def compose_row_sources(
    *groups: Iterable[Any],
) -> Mapping[type[Any], "RowSourceEmitter"]:
    registry: dict[type[Any], RowSourceEmitter] = {}
    for group in groups:
        for emitter in group:
            if emitter.node_type in registry:
                raise ValueError(
                    f"duplicate row-source emitter for {emitter.node_type!r}"
                )
            registry[emitter.node_type] = emitter
    return registry


DEFAULT_ROW_SOURCES = compose_row_sources(FAMILIES)

__all__ = ["DEFAULT_ROW_SOURCES", "FAMILIES", "compose_row_sources"]
