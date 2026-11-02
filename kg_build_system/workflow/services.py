"""Typed runtime capabilities shared by every workflow module.

The data a module reads is the module contract in
:mod:`kg_build_system.kernel.contract`, re-exported for compatibility from
:mod:`kg_build_system.workflow.models`. This module states the services the
runtime provides and their in-process implementations. The DuckDB relation
service itself belongs to the engine, in :mod:`kg_build_system.engines.interfaces`.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from .._relations import RelationQueryResult, RelationRef, RelationService


class WorkflowLogger(Protocol):
    """Step-scoped logging exposed to workflow module executors."""

    def debug(self, message: str, *args: object) -> None: ...

    def info(self, message: str, *args: object) -> None: ...

    def warning(self, message: str, *args: object) -> None: ...

    def error(self, message: str, *args: object) -> None: ...


class WorkingStorage(Protocol):
    """Storage rooted at a caller-selected build directory."""

    def child(self, relative_path: PurePosixPath) -> Path: ...


@dataclass(frozen=True, slots=True)
class LocalWorkingStorage:
    root: Path

    def child(self, relative_path: PurePosixPath) -> Path:
        return self.root.joinpath(*relative_path.parts)


@dataclass(frozen=True, slots=True)
class LocalTemporaryStorage:
    root: Path


class CredentialResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


@dataclass(frozen=True, slots=True)
class MappingCredentialResolver:
    credentials: Mapping[str, str]

    def resolve(self, reference: str) -> str:
        return self.credentials[reference]


@dataclass(frozen=True, slots=True)
class ExecutionServices:
    """Runtime facilities shared by every module."""

    relations: RelationService
    output_storage: WorkingStorage
    working_storage: WorkingStorage
    temporary_storage: LocalTemporaryStorage
    credentials: CredentialResolver
    logger: WorkflowLogger


__all__ = [
    "CredentialResolver",
    "ExecutionServices",
    "LocalTemporaryStorage",
    "LocalWorkingStorage",
    "MappingCredentialResolver",
    "RelationQueryResult",
    "RelationRef",
    "RelationService",
    "WorkflowLogger",
    "WorkingStorage",
]
