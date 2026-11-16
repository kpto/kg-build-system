"""Transcribe source and derived relation declarations into the data DTO."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from kg_build_system.distribution.languages.annotations.service.internal import annotation_dtos
from kg_build_system.distribution.languages.annotations.model.internal import AnnotationDTO
from kg_build_system.distribution.languages.asset.model.public import (
    asset_reference,
)
from kg_build_system.distribution.languages.expressions.service.internal import expression_dto
from kg_build_system.distribution.model.public.refs import FieldRef
from kg_build_system.kernel import Key
from kg_build_system.kernel.service.internal.types import type_to_dto
from ...model.internal.dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, DefinitionDTO, DerivedRelationDTO,
    FieldDefinitionDTO, SourceRelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOrderByDTO, RowScanDTO,
    RowSourcePlanDTO, RowUnionDTO, StructDTO,
)
from ...model.public.row_sources import RowSource
from .declarations import DeclarationSpec, is_source_relation_group, derived_relation_row_source
from .groups import group_source_relations
from .rows import plan_scan_sources, row_source_plan_dto

_DECLARATION_KINDS = {
    "source_relation", "struct", "computed_struct", "derived_relation", "stage",
}


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
        elif spec.kind == "source_relation_group" and spec.final:
            for member in spec.members:
                _walk(member, found, seen)
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
    """Select data declarations reachable from a namespace."""
    values = tuple(namespace.values())
    found, _ = collect_declarations(values)
    result: list[object] = []
    seen: set[int] = set()
    for value in found.values():
        if id(value) in seen:
            continue
        seen.add(id(value))
        result.append(value)
    return tuple(result)


def _data_annotations(values: Sequence[Any]) -> tuple[AnnotationDTO, ...]:
    return annotation_dtos(values)


def _meaning_dto(value: Any) -> Any:
    if value is None:
        return None
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_to_dto,
    )

    return meaning_to_dto(value)


def _definition_dto(value: Any) -> DefinitionDTO | None:
    if value is None:
        return None
    return DefinitionDTO(grain=value.grain, identity=tuple(value.identity))


def _field_definition_dto(value: Any) -> FieldDefinitionDTO | None:
    if value is None:
        return None
    return FieldDefinitionDTO(
        value=value.value,
        unit=value.unit,
        null_meaning=value.null_meaning,
    )


def _column(
    owner: str, item: Any, *, expression: bool = False,
) -> ColumnDTO:
    return ColumnDTO(
        name=item.name,
        logical_type=type_to_dto(item.logical_type),
        ref=FieldRef("data", Key((f"{owner}.{item.name}",))),
        annotations=_data_annotations(item.annotations),
        expression=(
            expression_dto(item.descriptor.expression.model)
            if expression and item.descriptor.expression is not None
            else None
        ),
        meaning=_meaning_dto(item.meaning),
        definition=_field_definition_dto(item.definition),
    )


def _struct(item: type[Any], spec: DeclarationSpec) -> StructDTO:
    name = spec.name or item.__name__
    return StructDTO(
        name=name,
        columns=tuple(_column(name, field) for field in spec.fields),
        annotations=_data_annotations(spec.annotations),
        meaning=_meaning_dto(spec.meaning),
    )


def _source_relation(item: type[Any], spec: DeclarationSpec) -> SourceRelationDTO:
    name = spec.name or item.__name__
    if spec.asset is None:
        raise ValueError(f"relation {name!r} has no logical asset")
    return SourceRelationDTO(
        name=name,
        columns=tuple(_column(name, field) for field in spec.fields),
        asset=asset_reference(spec.asset),
        annotations=_data_annotations(spec.annotations),
        meaning=_meaning_dto(spec.meaning),
        definition=_definition_dto(spec.definition),
    )


def _derived_relation(item: type[Any], spec: DeclarationSpec) -> DerivedRelationDTO:
    name = spec.name or item.__name__
    columns = []
    for field in spec.fields:
        if field.descriptor.expression is None:
            raise TypeError("derived relation outputs require computed_field()")
        columns.append(_column(name, field, expression=True))
    row_source = derived_relation_row_source(item)
    if row_source is None:
        raise ValueError("derived relations require a row source")
    plan = (
        row_source
        if isinstance(row_source, (
            RowScanDTO, RowFilterDTO, RowUnionDTO, RowJoinDTO,
            RowGroupByDTO, RowDistinctDTO, RowOrderByDTO,
        ))
        else row_source_plan_dto(row_source)
    )
    definition = _definition_dto(spec.definition)
    if definition is None:
        raise ValueError(
            "a derived relation requires a Contract with a Definition and a Meaning"
        )
    return DerivedRelationDTO(
        name=name,
        columns=tuple(columns),
        row_source=cast(RowSourcePlanDTO, plan),
        definition=definition,
        annotations=_data_annotations(spec.annotations),
        visibility="internal" if spec.kind == "stage" else "public",
        meaning=_meaning_dto(spec.meaning),
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
    for value in declarations:
        if isinstance(value, type) and is_source_relation_group(value):
            for source_relation, _ in group_source_relations(value):
                found.setdefault(id(source_relation), source_relation)

    source_relations: dict[int, type[Any]] = {}
    derived_relations: dict[int, type[Any]] = {}
    struct_roots: list[type[Any]] = []
    for declaration in found.values():
        spec = _spec(declaration)
        if spec is None or not spec.final:
            continue
        if spec.kind == "source_relation":
            source_relations[id(declaration)] = declaration
        elif spec.kind in {"derived_relation", "stage"}:
            derived_relations[id(declaration)] = declaration
        elif spec.kind in {"struct", "computed_struct"}:
            struct_roots.append(declaration)
    structs: dict[int, type[Any]] = {id(item): item for item in struct_roots}
    _add_struct_closure(
        (*source_relations.values(), *derived_relations.values(), *struct_roots),
        structs,
    )

    return DataPartDTO(
        structs=tuple(sorted(
            (
                _struct(item, cast(DeclarationSpec, _spec(item)))
                for item in structs.values()
            ),
            key=lambda item: item.name,
        )),
        source_relations=tuple(sorted(
            (
                _source_relation(item, cast(DeclarationSpec, _spec(item)))
                for item in source_relations.values()
            ),
            key=lambda item: item.name,
        )),
        derived_relations=tuple(sorted(
            (
                _derived_relation(item, cast(DeclarationSpec, _spec(item)))
                for item in derived_relations.values()
            ),
            key=lambda item: item.name,
        )),
    )


def validate_data(data: DataPartDTO) -> None:
    """Reject a data DTO that violates the language invariants."""
    source_relation_names = tuple(item.name for item in data.source_relations)
    derived_relation_names = tuple(item.name for item in data.derived_relations)
    if len(source_relation_names) != len(set(source_relation_names)):
        raise ValueError("source relation names must be unique")
    if len(derived_relation_names) != len(set(derived_relation_names)):
        raise ValueError("derived relation names must be unique")
    if len(set(source_relation_names) | set(derived_relation_names)) != (
        len(source_relation_names) + len(derived_relation_names)
    ):
        raise ValueError("source and derived relation names must be unique")
    for declaration in (*data.structs, *data.source_relations, *data.derived_relations):
        names = tuple(column.name for column in declaration.columns)
        if len(names) != len(set(names)):
            raise ValueError(f"{declaration.name} column names must be unique")
    known = set(source_relation_names) | set(derived_relation_names)
    for source_relation in data.source_relations:
        if source_relation.asset is None:
            raise ValueError(
                f"source relation {source_relation.name!r} must name its logical asset"
            )
    for derived_relation in data.derived_relations:
        unknown = set(plan_scan_sources(derived_relation.row_source)) - known
        if unknown:
            raise ValueError(
                "derived relation row source reads unknown logical source "
                + ", ".join(sorted(unknown))
            )
        if derived_relation.definition is None:
            raise ValueError(
                "a derived relation requires a Contract with a Definition "
                "and a Meaning"
            )
        if derived_relation.visibility == "internal":
            if derived_relation.meaning is not None:
                raise ValueError("a stage carries no contract meaning")
            continue
        if (
            derived_relation.meaning is None
            or derived_relation.meaning.purpose is None
        ):
            raise ValueError("a derived relation contract requires a purpose")
    for source_relation in data.source_relations:
        if (source_relation.definition is None) != (
            source_relation.meaning is None
        ):
            raise ValueError(
                "a declared contract requires a Definition and a Meaning"
            )


__all__ = [
    "collect_declarations", "collect_values", "transcribe_data", "validate_data",
]
