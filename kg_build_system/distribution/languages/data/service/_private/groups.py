"""Table-group expansion and validation.

A group is a catalog of concrete tables and nested groups. It carries no
physical source: every member table names its own asset, so expanding a group
only flattens it into member tables and their canonical catalog paths.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .declarations import DeclarationSpec, is_concrete_table, is_table_group

if TYPE_CHECKING:
    from ...model.public.declarations import TableGroup


def _declaration_spec(value: type) -> DeclarationSpec | None:
    spec = vars(value).get("_kg_declaration_spec")
    return spec if isinstance(spec, DeclarationSpec) else None


def group_name(group: type) -> str:
    """Return the logical name of one table group."""
    spec = _declaration_spec(group)
    name = spec.name if spec is not None else None
    if name is None:
        name = getattr(group, "_table_group_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("table groups require a logical name")
    return name


def group_members(group: type) -> tuple[type, ...]:
    """Return the declared members of one table group."""
    spec = _declaration_spec(group)
    members = spec.members if spec is not None else ()
    if not members:
        members = tuple(getattr(group, "_table_group_entries", ()))
    return members


def table_name(table: type) -> str:
    """Return the logical name of one concrete table."""
    spec = _declaration_spec(table)
    name = spec.name if spec is not None else None
    if name is None:
        name = getattr(table, "_table_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("tables require a logical name")
    return name


def group_tables(
    group: type,
    prefix: tuple[str, ...] = (),
    visited: tuple[type, ...] = (),
) -> tuple[tuple[type, tuple[str, ...]], ...]:
    """Flatten a group into concrete tables and canonical catalog paths."""
    if group in visited:
        raise TypeError("table groups may not contain a cycle")
    path = (*prefix, group_name(group))
    result: list[tuple[type, tuple[str, ...]]] = []
    for target in group_members(group):
        if is_concrete_table(target):
            result.append((target, (*path, table_name(target))))
        else:
            result.extend(group_tables(target, path, (*visited, group)))
    tables = tuple(table for table, _ in result)
    paths = tuple(catalog_path for _, catalog_path in result)
    if len(set(tables)) != len(tables):
        raise TypeError("a table group may include a final table only once")
    if len(set(paths)) != len(paths):
        raise TypeError("a table group has duplicate catalog paths")
    return tuple(result)


__all__ = [
    "group_members", "group_name", "group_tables", "table_name",
]
