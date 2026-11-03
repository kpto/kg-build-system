"""Typed runtime capabilities shared by instruction executors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...internal.relations import RelationService
from ..storage import (
    CredentialResolver,
    LocalTemporaryStorage,
    WorkingStorage,
)


class WorkflowLogger(Protocol):
    """Step-scoped logging exposed to instruction executors."""

    def debug(self, message: str, *args: object) -> None:
        """Log one debug message."""
        ...

    def info(self, message: str, *args: object) -> None:
        """Log one informational message."""
        ...

    def warning(self, message: str, *args: object) -> None:
        """Log one warning."""
        ...

    def error(self, message: str, *args: object) -> None:
        """Log one error."""
        ...


@dataclass(frozen=True, slots=True)
class ExecutionServices:
    """Runtime facilities shared by every instruction executor."""

    relations: RelationService
    output_storage: WorkingStorage
    working_storage: WorkingStorage
    temporary_storage: LocalTemporaryStorage
    credentials: CredentialResolver
    logger: WorkflowLogger


__all__ = ["ExecutionServices", "WorkflowLogger"]
