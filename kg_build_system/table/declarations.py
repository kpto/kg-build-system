"""Factories and source resolution for logical data declarations."""
from __future__ import annotations

from dataclasses import replace

from ..annotations import annotation_tuple
from .fields import field
from .models import (
    BoundSource,
    BoundTable,
    BoundTableGroup,
    DataSourceConfig,
    SourceBindingOptions,
    is_concrete_table,
    is_table_group,
)
from .projections import projection_field


def group_tables(
    group: type,
    prefix: tuple[str, ...] = (),
    visited: tuple[type, ...] = (),
) -> tuple[tuple[type, tuple[str, ...]], ...]:
    """Flatten a group into concrete tables and canonical catalog paths."""
    if group in visited:
        raise TypeError("table groups may not contain a cycle")
    path = (*prefix, group._table_group_name)
    result: list[tuple[type, tuple[str, ...]]] = []
    for target in group._table_group_entries:
        if is_concrete_table(target):
            result.append((target, (*path, target._table_name)))
        else:
            result.extend(group_tables(target, path, (*visited, group)))
    tables = tuple(table for table, _ in result)
    paths = tuple(catalog_path for _, catalog_path in result)
    if len(set(tables)) != len(tables):
        raise TypeError("a table group may include a final table only once")
    if len(set(paths)) != len(paths):
        raise TypeError("a table group has duplicate catalog paths")
    return tuple(result)


def _location_for(
    config: DataSourceConfig,
    group_path: tuple[str, ...],
    table_name: str,
) -> str:
    if config.layout is None:
        raise ValueError(
            "group sources require DataSourceConfig.layout to resolve each table"
        )
    try:
        relative = config.layout.format(
            group_path="/".join(group_path), table_name=table_name
        )
    except (IndexError, KeyError) as error:
        raise ValueError(
            "group source layouts may use only {group_path} and {table_name}"
        ) from error
    return f"{config.location.rstrip('/\\')}/{relative.lstrip('/\\')}"


def resolve_bound_source(source: BoundSource) -> tuple[BoundTable, ...]:
    if isinstance(source, BoundTable):
        return (source,)
    return tuple(
        BoundTable(
            table,
            replace(
                source.config,
                location=_location_for(source.config, path[:-1], path[-1]),
                layout=None,
            ),
            source.annotations,
        )
        for table, path in group_tables(source.group)
    )


def bind_source(
    *,
    target: type,
    config: DataSourceConfig,
    options: SourceBindingOptions = SourceBindingOptions(),
) -> BoundSource:
    annotations = annotation_tuple(options.annotations)
    if is_concrete_table(target):
        return BoundTable(target, config, annotations)
    if is_table_group(target):
        return BoundTableGroup(target, config, annotations)
    raise TypeError("sources require a final Table or TableGroup")


__all__ = [
    "bind_source",
    "field",
    "group_tables",
    "projection_field",
    "resolve_bound_source",
]
