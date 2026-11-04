"""The engine's relation reference and query result values.

The shared ``RelationService`` protocol lives in
:mod:`kg_build_system.distribution.service.internal.relations`; the DuckDB
engine implements it and owns these two values.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
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


__all__ = ["RelationQueryResult", "RelationRef"]
