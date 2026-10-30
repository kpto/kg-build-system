"""Composition of DuckDB row-source lowerers, keyed by plan node type."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ....protocols import RowSourceLowerer
from .distinct import DistinctLowerer
from .filter import FilterLowerer
from .group_by import GroupByLowerer
from .join import JoinLowerer
from .order_by import OrderByLowerer
from .scan import ScanLowerer
from .union import UnionLowerer

FAMILIES = (
    ScanLowerer(),
    FilterLowerer(),
    UnionLowerer(),
    DistinctLowerer(),
    OrderByLowerer(),
    JoinLowerer(),
    GroupByLowerer(),
)


def compose_row_sources(
    *groups: Iterable[RowSourceLowerer],
) -> Mapping[type[Any], RowSourceLowerer]:
    registry: dict[type[Any], RowSourceLowerer] = {}
    for group in groups:
        for lowerer in group:
            if lowerer.node_type in registry:
                raise ValueError(
                    f"duplicate row-source lowerer for {lowerer.node_type!r}"
                )
            registry[lowerer.node_type] = lowerer
    return registry


DEFAULT_ROW_SOURCES = compose_row_sources(FAMILIES)

__all__ = ["DEFAULT_ROW_SOURCES", "FAMILIES", "compose_row_sources"]
