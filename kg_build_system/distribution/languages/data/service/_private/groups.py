"""Source-relation-group expansion and validation.

A group is a catalog of concrete source relations and nested groups. It carries
no physical source: every member source relation names its own asset, so
expanding a group only flattens it into member source relations and their
canonical catalog paths.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .declarations import DeclarationSpec, is_concrete_source_relation, is_source_relation_group

if TYPE_CHECKING:
    from ...model.public.declarations import SourceRelationGroup


def _declaration_spec(value: type) -> DeclarationSpec | None:
    spec = vars(value).get("_kg_declaration_spec")
    return spec if isinstance(spec, DeclarationSpec) else None


def group_name(group: type) -> str:
    """Return the logical name of one source relation group."""
    spec = _declaration_spec(group)
    name = spec.name if spec is not None else None
    if name is None:
        name = getattr(group, "_source_relation_group_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("source relation groups require a logical name")
    return name


def group_members(group: type) -> tuple[type, ...]:
    """Return the declared members of one source relation group."""
    spec = _declaration_spec(group)
    members = spec.members if spec is not None else ()
    if not members:
        members = tuple(getattr(group, "_source_relation_group_entries", ()))
    return members


def source_relation_name(source_relation: type) -> str:
    """Return the logical name of one concrete source relation."""
    spec = _declaration_spec(source_relation)
    name = spec.name if spec is not None else None
    if name is None:
        name = getattr(source_relation, "_source_relation_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("source relations require a logical name")
    return name


def group_source_relations(
    group: type,
    prefix: tuple[str, ...] = (),
    visited: tuple[type, ...] = (),
) -> tuple[tuple[type, tuple[str, ...]], ...]:
    """Flatten a group into concrete source relations and canonical catalog paths."""
    if group in visited:
        raise TypeError("source relation groups may not contain a cycle")
    path = (*prefix, group_name(group))
    result: list[tuple[type, tuple[str, ...]]] = []
    for target in group_members(group):
        if is_concrete_source_relation(target):
            result.append((target, (*path, source_relation_name(target))))
        else:
            result.extend(group_source_relations(target, path, (*visited, group)))
    source_relations = tuple(source_relation for source_relation, _ in result)
    paths = tuple(catalog_path for _, catalog_path in result)
    if len(set(source_relations)) != len(source_relations):
        raise TypeError("a source relation group may include a final source relation only once")
    if len(set(paths)) != len(paths):
        raise TypeError("a source relation group has duplicate catalog paths")
    return tuple(result)


__all__ = [
    "group_members", "group_name", "group_source_relations",
    "source_relation_name",
]
