"""Filesystem walking that collapses partitions and parts into logical datasets."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import urlparse

import fsspec
from fsspec import AbstractFileSystem

from ..models import GenerationError
from .formats import DATA_SUFFIXES, HIVE_PARTITION, PARQUET_SUFFIXES, source_stem


@dataclass(frozen=True)
class LogicalTable:
    group_path: tuple[str, ...]
    name: str
    sources: tuple[str, ...]
    hive_partitioned: bool = False


def _filesystem_source(filesystem: AbstractFileSystem, path: str) -> str:
    value = filesystem.unstrip_protocol(path)
    if isinstance(value, str) and value.startswith("file://"):
        return str(Path(value[7:]).resolve())
    return str(value)


def logical_tables(
    source: str,
    request_id: str,
    layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"],
    *,
    anonymous: bool = False,
) -> tuple[LogicalTable, ...]:
    """Walk a filesystem and collapse partitions/parts into logical datasets."""
    storage_options = {"anon": True} if urlparse(source).scheme.lower() == "s3" and anonymous else {}
    filesystem, root = fsspec.core.url_to_fs(source, **storage_options)
    if filesystem.isfile(root):
        return (LogicalTable((), source_stem(source), (source,)),)
    if not filesystem.isdir(root):
        raise GenerationError(f"data-contract inference input does not exist: {source}")

    root_path = PurePosixPath(str(root).replace("\\", "/").rstrip("/"))
    grouped: dict[tuple[tuple[str, ...], str], list[tuple[str, bool]]] = {}
    for raw_path in sorted(filesystem.find(root)):
        if not filesystem.isfile(raw_path):
            continue
        path = PurePosixPath(str(raw_path).replace("\\", "/"))
        suffix = path.suffix.lower()
        if suffix not in DATA_SUFFIXES:
            continue
        if layout != "files" and suffix not in PARQUET_SUFFIXES:
            continue
        try:
            relative = path.relative_to(root_path)
        except ValueError as error:
            raise GenerationError(f"filesystem returned a path outside the inference root: {raw_path}") from error
        parents = relative.parts[:-1]
        partitioned = layout == "hive_partitioned_parquet" and any(
            HIVE_PARTITION.fullmatch(part) for part in parents
        )
        logical_parents = tuple(
            part for part in parents
            if layout != "hive_partitioned_parquet" or not HIVE_PARTITION.fullmatch(part)
        )
        if layout != "files":
            if logical_parents:
                group_path, table_name = logical_parents[:-1], logical_parents[-1]
            else:
                group_path, table_name = (), request_id
        else:
            group_path, table_name = logical_parents, path.stem
        grouped.setdefault((group_path, table_name), []).append(
            (_filesystem_source(filesystem, str(raw_path)), partitioned)
        )
    if not grouped:
        raise GenerationError(f"data input {source} contains no supported relations")
    return tuple(
        LogicalTable(group_path, name, tuple(item[0] for item in files), any(item[1] for item in files))
        for (group_path, name), files in sorted(grouped.items())
    )


__all__ = ["LogicalTable", "logical_tables"]
