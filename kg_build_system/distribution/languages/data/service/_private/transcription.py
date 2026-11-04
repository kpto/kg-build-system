"""Transcribe table declarations into the data language's blueprint DTO."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from kg_build_system.distribution.languages.annotations.service.internal import annotation_dtos
from kg_build_system.distribution.languages.annotations.model.internal import AnnotationDTO
from kg_build_system.distribution.languages.expressions.service.internal import expression_dto
from kg_build_system.kernel.service.internal.types import type_to_dto
from ...model.internal.dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, ProjectionDTO, RelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOrderByDTO, RowScanDTO,
    RowSourcePlanDTO, RowUnionDTO, SourceDTO, StructDTO,
)
from ...model.public.row_sources import RowSource
from ...model.public.sources import BoundSource, BoundTable
from .declarations import DeclarationSpec, is_table_group, projection_row_source
from .rows import plan_scan_sources, row_source_plan_dto
from .sources import group_tables, resolve_bound_source

_DECLARATION_KINDS = {"table", "struct", "computed_struct", "projection"}


def _spec(value: Any) -> DeclarationSpec | None:
    if not isinstance(value, type):
        return None
    spec = vars(value).get("_kg_declaration_spec")
    return spec if isinstance(spec, DeclarationSpec) else None


def _walk(value: Any, found: dict[int, Any], seen: set[int]) -> None:
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)
    if isinstance(value, type):
        spec = _spec(value)
        if spec is None:
            return
        if spec.kind in _DECLARATION_KINDS and spec.final:
            found[marker] = value
            for item in spec.fields:
                _walk(item.declaration, found, seen)
            _walk(spec.row_source, found, seen)
        elif spec.kind == "table_group" and spec.final:
            for member in spec.members:
                _walk(member, found, seen)
        return
    if isinstance(value, BoundSource):
        target = value.table if isinstance(value, BoundTable) else value.group
        _walk(target, found, seen)
        return
    if isinstance(value, RowSource):
        _walk(getattr(value, "source", None), found, seen)
        return
    rows = getattr(value, "rows", None)
    if rows is not None:
        _walk(rows, found, seen)


def collect_declarations(values: Sequence[Any]) -> tuple[dict[int, Any], dict[int, Any]]:
    """Return every reachable declaration and its nested structs."""
    found: dict[int, Any] = {}
    structs: dict[int, Any] = {}
    seen: set[int] = set()
    for value in values:
        _walk(value, found, seen)
    return found, structs


def collect_values(namespace: Any) -> tuple[object, ...]:
    """Select table declarations and source bindings from a namespace."""
    values = tuple(namespace.values())
    found, _ = collect_declarations(values)
    sources = tuple(value for value in values if isinstance(value, BoundSource))
    result: list[object] = []
    seen: set[int] = set()
    for value in (*found.values(), *sources):
        if id(value) in seen:
            continue
        seen.add(id(value))
        result.append(value)
    return tuple(result)


def _data_annotations(values: Sequence[Any]) -> tuple[AnnotationDTO, ...]:
    return annotation_dtos(values)


def _column(item: Any, *, expression: bool = False) -> ColumnDTO:
    return ColumnDTO(
        name=item.name,
        logical_type=type_to_dto(item.logical_type),
        description=item.description,
        annotations=_data_annotations(item.annotations),
        expression=(
            expression_dto(item.descriptor.expression.model)
            if expression and item.descriptor.expression is not None
            else None
        ),
    )


def _struct(item: type[Any], spec: DeclarationSpec) -> StructDTO:
    return StructDTO(
        name=spec.name or item.__name__,
        columns=tuple(_column(field) for field in spec.fields),
        description=spec.description,
        annotations=_data_annotations(spec.annotations),
    )


def _relation(item: type[Any], spec: DeclarationSpec) -> RelationDTO:
    return RelationDTO(
        name=spec.name or item.__name__,
        columns=tuple(_column(field) for field in spec.fields),
        description=spec.description,
        annotations=_data_annotations(spec.annotations),
    )


def _projection(item: type[Any], spec: DeclarationSpec) -> ProjectionDTO:
    columns = []
    for field in spec.fields:
        if field.descriptor.expression is None:
            raise TypeError("projection outputs require computed_field()")
        columns.append(_column(field, expression=True))
    row_source = projection_row_source(item)
    if row_source is None:
        raise ValueError("projections require a row source")
    plan = (
        row_source
        if isinstance(row_source, (
            RowScanDTO, RowFilterDTO, RowUnionDTO, RowJoinDTO,
            RowGroupByDTO, RowDistinctDTO, RowOrderByDTO,
        ))
        else row_source_plan_dto(row_source)
    )
    return ProjectionDTO(
        name=spec.name or item.__name__,
        columns=tuple(columns),
        row_source=cast(RowSourcePlanDTO, plan),
        description=spec.description,
        annotations=_data_annotations(spec.annotations),
    )


def _source(source: BoundTable) -> SourceDTO:
    table = source.table
    spec = _spec(table)
    name = spec.name if spec is not None and spec.name else table.__name__
    annotations = tuple(spec.annotations if spec is not None else ())
    return SourceDTO(
        table=name,
        location=source.config.location,
        format=source.config.format.value,
        credential_reference=source.config.credentials,
        version=source.config.version,
        annotations=_data_annotations((*annotations, *source.annotations)),
    )


def _nested_declarations(field: Any) -> tuple[type[Any], ...]:
    declaration = field.declaration
    return (declaration,) if isinstance(declaration, type) else ()


def _add_struct_closure(
    roots: Sequence[type[Any]], structs: dict[int, type[Any]],
) -> None:
    queue = list(roots)
    seen: set[int] = set()
    while queue:
        declaration = queue.pop()
        marker = id(declaration)
        if marker in seen:
            continue
        seen.add(marker)
        spec = _spec(declaration)
        if spec is None or not spec.final:
            continue
        if spec.kind in {"struct", "computed_struct"}:
            structs[marker] = declaration
        for item in spec.fields:
            for nested in _nested_declarations(item):
                nested_spec = _spec(nested)
                if nested_spec is not None and nested_spec.kind in {
                    "struct", "computed_struct",
                }:
                    queue.append(nested)


def transcribe_data(declarations: Sequence[object]) -> DataPartDTO:
    """Transcribe collected declarations into the data language DTO."""
    found, _ = collect_declarations(tuple(declarations))
    bound_tables: list[BoundTable] = []
    for value in declarations:
        if isinstance(value, BoundSource):
            bound_tables.extend(resolve_bound_source(value))
        elif isinstance(value, type) and is_table_group(value):
            for table, _ in group_tables(value):
                found.setdefault(id(table), table)
    for source in bound_tables:
        found.setdefault(id(source.table), source.table)

    relations: dict[int, type[Any]] = {}
    projections: dict[int, type[Any]] = {}
    struct_roots: list[type[Any]] = []
    for declaration in found.values():
        spec = _spec(declaration)
        if spec is None or not spec.final:
            continue
        if spec.kind == "table":
            relations[id(declaration)] = declaration
        elif spec.kind == "projection":
            projections[id(declaration)] = declaration
        elif spec.kind in {"struct", "computed_struct"}:
            struct_roots.append(declaration)
    structs: dict[int, type[Any]] = {id(item): item for item in struct_roots}
    _add_struct_closure(
        (*relations.values(), *projections.values(), *struct_roots), structs,
    )

    return DataPartDTO(
        structs=tuple(sorted(
            (
                _struct(item, cast(DeclarationSpec, _spec(item)))
                for item in structs.values()
            ),
            key=lambda item: item.name,
        )),
        relations=tuple(sorted(
            (
                _relation(item, cast(DeclarationSpec, _spec(item)))
                for item in relations.values()
            ),
            key=lambda item: item.name,
        )),
        projections=tuple(sorted(
            (
                _projection(item, cast(DeclarationSpec, _spec(item)))
                for item in projections.values()
            ),
            key=lambda item: item.name,
        )),
        sources=tuple(sorted(
            (_source(item) for item in bound_tables),
            key=lambda item: item.table,
        )),
    )


def validate_data(data: DataPartDTO) -> None:
    """Reject a data DTO that violates the language invariants."""
    relation_names = tuple(item.name for item in data.relations)
    projection_names = tuple(item.name for item in data.projections)
    if len(relation_names) != len(set(relation_names)):
        raise ValueError("relation names must be unique")
    if len(projection_names) != len(set(projection_names)):
        raise ValueError("projection names must be unique")
    if len(set(relation_names) | set(projection_names)) != (
        len(relation_names) + len(projection_names)
    ):
        raise ValueError("relation and projection names must be unique")
    for declaration in (*data.structs, *data.relations, *data.projections):
        names = tuple(column.name for column in declaration.columns)
        if len(names) != len(set(names)):
            raise ValueError(f"{declaration.name} column names must be unique")
    known = set(relation_names) | set(projection_names)
    for projection in data.projections:
        unknown = set(plan_scan_sources(projection.row_source)) - known
        if unknown:
            raise ValueError(
                "projection row source reads unknown logical source "
                + ", ".join(sorted(unknown))
            )
    source_tables = tuple(item.table for item in data.sources)
    if len(source_tables) != len(set(source_tables)):
        raise ValueError("source-bound relation names must be unique")
    unknown_sources = set(source_tables) - set(relation_names)
    if unknown_sources:
        raise ValueError(
            "a physical source references an unknown relation: "
            + ", ".join(sorted(unknown_sources))
        )


__all__ = [
    "collect_declarations", "collect_values", "transcribe_data", "validate_data",
]
