"""Relation and output adapters shared by the supplied target modules.

The kernel execution context supplies one ``services`` value. These functions
state the relation and storage operations the targets use, so each target does
not repeat the lookup.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any


def output_path(services: Any, relative_path: str) -> Path:
    """Resolve a relative path beneath the build output directory."""
    storage = services.output_storage
    if hasattr(storage, "child"):
        return storage.child(PurePosixPath(relative_path))
    return Path(storage).joinpath(*PurePosixPath(relative_path).parts)


def relation_service(services: Any) -> Any:
    service = getattr(services, "relations", services)
    if not hasattr(service, "query") and hasattr(services, "query"):
        return services
    return service


def reference(services: Any, value: Any) -> Any:
    return relation_service(services).reference(value)


def query(services: Any, sql: str, parameters: Any = None) -> Any:
    service = relation_service(services)
    if parameters is None:
        return service.query(sql)
    return service.query(sql, parameters)


def export_parquet(services: Any, sql: str, destination: Path) -> None:
    service = relation_service(services)
    if hasattr(service, "export_parquet"):
        service.export_parquet(sql, destination)
        return
    services.export_parquet(sql, destination)


def input_values(context: Any, name: str) -> tuple[Any, ...]:
    """The contributions received under one declared input name."""
    values = context.inputs.get(name, ())
    if values is None:
        return ()
    if isinstance(values, (tuple, list)):
        return tuple(values)
    return (values,)


def artifact_of(contribution: Any) -> Any | None:
    return getattr(contribution, "artifact", None)


__all__ = [
    "artifact_of", "export_parquet", "input_values", "output_path", "query",
    "reference", "relation_service",
]
