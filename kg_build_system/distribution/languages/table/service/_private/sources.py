"""Source-binding and table-group expansion mechanics."""
from __future__ import annotations

from dataclasses import replace
from string import Formatter
from typing import TYPE_CHECKING

from kg_build_system.distribution.languages.annotations.service.internal import annotation_tuple
from .declarations import DeclarationSpec, is_concrete_table, is_table_group

if TYPE_CHECKING:
    from ...model.public.sources import (
        BoundSource, BoundTable, BoundTableGroup, DataSourceConfig,
        SourceBindingOptions,
    )


def _declaration_spec(value: type) -> DeclarationSpec | None:
    spec = vars(value).get("_kg_declaration_spec")
    return spec if isinstance(spec, DeclarationSpec) else None


def _group_name(group: type) -> str:
    spec = _declaration_spec(group)
    name = spec.name if spec is not None else None
    if name is None:
        name = getattr(group, "_table_group_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("table groups require a logical name")
    return name


def _group_members(group: type) -> tuple[type, ...]:
    spec = _declaration_spec(group)
    members = spec.members if spec is not None else ()
    if not members:
        members = tuple(getattr(group, "_table_group_entries", ()))
    return members


def _table_name(table: type) -> str:
    spec = _declaration_spec(table)
    name = spec.name if spec is not None else None
    if name is None:
        name = getattr(table, "_table_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("tables require a logical name")
    return name


def make_bound_source(
    *,
    target: type,
    config: DataSourceConfig,
    options: SourceBindingOptions | None = None,
) -> BoundSource:
    """Bind a final table or table group to a configured data source."""
    from ...model.public.sources import BoundTable, BoundTableGroup, SourceBindingOptions

    resolved = SourceBindingOptions() if options is None else options
    annotations = annotation_tuple(resolved.annotations)
    if is_concrete_table(target):
        return BoundTable(target, config, annotations)
    if is_table_group(target):
        return BoundTableGroup(target, config, annotations)
    raise TypeError("sources require a final Table or TableGroup")


def group_tables(
    group: type,
    prefix: tuple[str, ...] = (),
    visited: tuple[type, ...] = (),
) -> tuple[tuple[type, tuple[str, ...]], ...]:
    """Flatten a group into concrete tables and canonical catalog paths."""
    if group in visited:
        raise TypeError("table groups may not contain a cycle")
    path = (*prefix, _group_name(group))
    result: list[tuple[type, tuple[str, ...]]] = []
    for target in _group_members(group):
        if is_concrete_table(target):
            result.append((target, (*path, _table_name(target))))
        else:
            result.extend(group_tables(target, path, (*visited, group)))
    tables = tuple(table for table, _ in result)
    paths = tuple(catalog_path for _, catalog_path in result)
    if len(set(tables)) != len(tables):
        raise TypeError("a table group may include a final table only once")
    if len(set(paths)) != len(paths):
        raise TypeError("a table group has duplicate catalog paths")
    return tuple(result)


def _layout_fields(layout: str) -> tuple[str, ...]:
    fields: list[str] = []
    for _, name, _, _ in Formatter().parse(layout):
        if name is not None:
            fields.append(name)
    return tuple(fields)


def _location_for(
    config: DataSourceConfig,
    group_path: tuple[str, ...],
    table_name: str,
) -> str:
    if config.layout is None:
        raise ValueError(
            "group sources require DataSourceConfig.layout to resolve each table"
        )
    allowed = {"group_path", "table_name"}
    if any(name not in allowed for name in _layout_fields(config.layout)):
        raise ValueError(
            "group source layouts may use only {group_path} and {table_name}"
        )
    try:
        relative = config.layout.format(
            group_path="/".join(group_path), table_name=table_name
        )
    except (IndexError, KeyError, ValueError) as error:
        raise ValueError(
            "group source layouts may use only {group_path} and {table_name}"
        ) from error
    return f"{config.location.rstrip('/\\')}/{relative.lstrip('/\\')}"


def resolve_bound_source(source: BoundSource) -> tuple[BoundTable, ...]:
    """Expand a source binding into one bound table per concrete table."""
    from ...model.public.sources import BoundTable

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


__all__ = ["group_tables", "make_bound_source", "resolve_bound_source"]
