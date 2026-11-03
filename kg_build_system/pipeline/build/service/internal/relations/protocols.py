"""Shared kernel: engine-neutral relational service protocols.

A workflow module and an engine implementation both depend on these names, so
they live below both. The protocols state what a module may ask of a relation;
the engine decides how it is executed.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RelationRef:
    """Opaque reference to a relation owned by the build runtime."""

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("relation name must be non-empty")


class RelationQueryResult(Protocol):
    """Synchronous result access executed through the relation worker."""

    @property
    def description(self) -> Sequence[Sequence[Any]]: ...

    def fetchone(self) -> Any: ...

    def fetchall(self) -> list[Any]: ...

    def fetchmany(self, size: int) -> list[Any]: ...


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


__all__ = ["RelationQueryResult", "RelationRef", "RelationService"]
