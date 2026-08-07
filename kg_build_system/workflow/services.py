"""Typed runtime capabilities shared by every workflow module."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol


class WorkingStorage(Protocol):
    """Storage rooted at a caller-selected build directory."""

    def child(self, relative_path: PurePosixPath) -> Path: ...


@dataclass(frozen=True)
class LocalWorkingStorage:
    root: Path

    def child(self, relative_path: PurePosixPath) -> Path:
        return self.root.joinpath(*relative_path.parts)


@dataclass(frozen=True)
class LocalTemporaryStorage:
    root: Path


class CredentialResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


@dataclass(frozen=True)
class MappingCredentialResolver:
    credentials: Mapping[str, str]

    def resolve(self, reference: str) -> str:
        return self.credentials[reference]


@dataclass(frozen=True)
class ExecutionServices:
    """Runtime facilities shared by every module.

    DuckDB is intentionally exposed directly while workflow modules are still
    expected to push relational work into it.
    """

    duckdb: Any
    output_storage: WorkingStorage
    working_storage: WorkingStorage
    temporary_storage: LocalTemporaryStorage
    credentials: CredentialResolver
