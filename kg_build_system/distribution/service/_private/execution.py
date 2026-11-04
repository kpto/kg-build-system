"""Relation and output adapters shared by the distribution modules.

A module receives a resource view from the kernel and asks for the relation
behind an artifact, a query result, an output path or the values a step received
under one input name. The adapters read only resources the executor declared.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from kg_build_system.distribution.modules.runtime.model.public import (
    OutputStorage,
)


def output_path(resources: Any, relative_path: str) -> Path:
    """Resolve a relative path beneath the build output directory."""
    storage = resources.get(OutputStorage)
    return storage.child(PurePosixPath(relative_path))


def relation_service(resources: Any) -> Any:
    """The relation service this executor declared."""
    from ..internal.relations import RelationService

    return resources.get(RelationService)


def reference(resources: Any, value: Any) -> Any:
    """The queryable reference behind one relational artifact value."""
    return relation_service(resources).reference(value)


def query(resources: Any, sql: str, parameters: Any = None) -> Any:
    """Run one query through the relation service."""
    service = relation_service(resources)
    if parameters is None:
        return service.query(sql)
    return service.query(sql, parameters)


def export_parquet(resources: Any, sql: str, destination: Path) -> None:
    """Write one query result to a Parquet file."""
    relation_service(resources).export_parquet(sql, destination)


def input_values(context: Any, name: str) -> tuple[Any, ...]:
    """The contributions received under one declared input name."""
    values = context.inputs.get(name, ())
    if values is None:
        return ()
    if isinstance(values, (tuple, list)):
        return tuple(values)
    return (values,)


def artifact_of(contribution: Any) -> Any | None:
    """The artifact carried by one input contribution, if any."""
    return getattr(contribution, "artifact", None)


__all__ = [
    "artifact_of", "export_parquet", "input_values", "output_path", "query",
    "reference", "relation_service",
]
