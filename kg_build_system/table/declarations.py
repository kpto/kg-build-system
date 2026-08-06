"""Factories and source resolution for final table declarations."""
from __future__ import annotations

from dataclasses import replace
from typing import Sequence, TypeVar

from ..annotations import Annotation, annotation_tuple
from ..expressions import Expression, ValueRef
from .models import (
    BoundSource, BoundTable, BoundTableGroup, CollectionField, DataSourceConfig, Field,
    CollectionItem, FieldValue, ProjectedField, SourceBindingOptions, Struct, StructField, TablePathValueRefMetadata, TableValue,
)


T = TypeVar("T", bound=FieldValue)
S = TypeVar("S", bound=Struct)


def field[T: FieldValue](*, name: str | None = None, description: str | None = None, annotations: Sequence[Annotation] = ()) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return Field(_metadata=TablePathValueRefMetadata(name=name, description=description, annotations=annotation_tuple(list(annotations))))


def struct_field(*, name: str | None = None, description: str | None = None, annotations: Sequence[Annotation] = ()) -> StructField[S]:  # pyright: ignore[reportInvalidTypeVarUse]
    return StructField(_metadata=TablePathValueRefMetadata(name=name, description=description, annotations=annotation_tuple(list(annotations))))


def collection_field[T: CollectionItem](*, name: str | None = None, description: str | None = None, annotations: Sequence[Annotation] = ()) -> CollectionField[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return CollectionField(_metadata=TablePathValueRefMetadata(name=name, description=description, annotations=annotation_tuple(list(annotations))))


def projected_field[T: TableValue](value: Expression[T] | ValueRef[T], *, annotations: Sequence[Annotation] = ()) -> ProjectedField[T]:
    return ProjectedField(value, annotations=annotation_tuple(list(annotations)))


def is_concrete_table(cls: type) -> bool:
    return vars(cls).get("_data_declaration_kind") == "table"


def _is_table_group(cls: type) -> bool:
    return bool(vars(cls).get("_is_table_group", False))


def _group_tables(
    group: type, prefix: tuple[str, ...] = (), visited: tuple[type, ...] = (),
) -> tuple[tuple[type, tuple[str, ...]], ...]:
    if group in visited:
        raise TypeError("table groups may not contain a cycle")
    path = prefix + (group._table_group_name,)
    result: list[tuple[type, tuple[str, ...]]] = []
    for target in group._table_group_entries:
        if is_concrete_table(target):
            result.append((target, path + (target._table_name,)))
        else:
            result.extend(_group_tables(target, path, visited + (group,)))
    tables = [table for table, _ in result]
    paths = [catalog_path for _, catalog_path in result]
    if len(set(tables)) != len(tables):
        raise TypeError("a table group may include a final table only once")
    if len(set(paths)) != len(paths):
        raise TypeError("a table group has duplicate catalog paths")
    return tuple(result)


def _location_for(config: DataSourceConfig, group_path: tuple[str, ...], table_name: str) -> str:
    if config.layout is None:
        raise ValueError("group sources require DataSourceConfig.layout to resolve each final resource address")
    try:
        relative_location = config.layout.format(group_path="/".join(group_path), table_name=table_name)
    except (IndexError, KeyError) as error:
        raise ValueError("group source layouts may use only {group_path} and {table_name}") from error
    return f"{config.location.rstrip('/\\')}/{relative_location.lstrip('/\\')}"


def resolve_bound_source(source: BoundSource) -> tuple[BoundTable, ...]:
    if isinstance(source, BoundTable):
        return (source,)
    return tuple(
        BoundTable(table, replace(source.config, location=_location_for(source.config, path[:-1], path[-1]), layout=None), source.annotations)
        for table, path in _group_tables(source.group)
    )


def bind_source(*, target: type, config: DataSourceConfig, options: SourceBindingOptions = SourceBindingOptions()) -> BoundSource:
    resolved_annotations = annotation_tuple(options.annotations)
    if is_concrete_table(target):
        return BoundTable(target, config, resolved_annotations)
    if _is_table_group(target):
        return BoundTableGroup(target, config, resolved_annotations)
    raise TypeError("sources require a final Table or TableGroup")
