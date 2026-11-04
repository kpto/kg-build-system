"""Stable internal interface for the shared execution helpers.

The implementation lives in :mod:`distribution.service._private.execution`; each
function here is a thin delegation so a module never imports a private zone.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def output_path(resources: Any, relative_path: str) -> Path:
    """Resolve a relative path beneath the build output directory."""
    from .._private.execution import output_path as implementation

    return implementation(resources, relative_path)


def relation_service(resources: Any) -> Any:
    """The relation service declared by one executor."""
    from .._private.execution import relation_service as implementation

    return implementation(resources)


def reference(resources: Any, value: Any) -> Any:
    """The queryable reference behind one relational artifact value."""
    from .._private.execution import reference as implementation

    return implementation(resources, value)


def query(resources: Any, sql: str, parameters: Any = None) -> Any:
    """Run one query through the relation service."""
    from .._private.execution import query as implementation

    return implementation(resources, sql, parameters)


def export_parquet(resources: Any, sql: str, destination: Path) -> None:
    """Write one query result to a Parquet file."""
    from .._private.execution import export_parquet as implementation

    implementation(resources, sql, destination)


def input_values(context: Any, name: str) -> tuple[Any, ...]:
    """The contributions received under one declared input name."""
    from .._private.execution import input_values as implementation

    return implementation(context, name)


def artifact_of(contribution: Any) -> Any | None:
    """The artifact carried by one input contribution, if any."""
    from .._private.execution import artifact_of as implementation

    return implementation(contribution)


__all__ = [
    "artifact_of", "export_parquet", "input_values", "output_path", "query",
    "reference", "relation_service",
]
