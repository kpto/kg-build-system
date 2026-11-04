"""The relational service protocol a workflow module may depend on.

A module asks for a logical relation, a query result or a Parquet export; the
engine decides how it is executed. The protocol is the shared interface between
the distribution modules and the DuckDB implementation.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from kg_build_system.distribution.modules.duckdb.model.public.relations import (
        RelationQueryResult,
        RelationRef,
    )


class RelationService(Protocol):
    """Executor-owned relational operations available to workflow modules."""

    def reference(self, value: object) -> str: ...

    def view(self, name: str, query: str) -> RelationRef:
        """Expose a logical relation without materializing its query."""
        ...

    def materialize(
        self, name: str, query: str, parameters: Sequence[object] = (),
    ) -> RelationRef:
        """Expose a logical relation backed by a private materialized table."""
        ...

    def query(
        self, query: str, parameters: Sequence[object] = (),
    ) -> RelationQueryResult: ...

    def export_parquet(
        self, query: str, destination: Path, *, compression: str = "zstd",
    ) -> None: ...

    def register_filesystem(self, filesystem: object) -> None: ...


__all__ = ["RelationService"]
