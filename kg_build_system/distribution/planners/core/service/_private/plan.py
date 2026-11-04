"""What the core planner needs to know about the graph blueprint.

This module owns ordering, the declaration shape map and the declared-null path
set. It does not build steps and it does not emit SQL.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kg_build_system.distribution.executors.duckdb.service.internal.emitters import (
    PARQUET_LIST_WRAPPER_PATH,
)
from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.expressions.model.internal import (
    FieldReferenceDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    walk_expression_dto,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ColumnDTO,
    ProjectionDTO,
    RelationDTO,
    RowScanDTO,
    RowSourcePlanDTO,
    StructDTO,
)
from kg_build_system.distribution.languages.data.model.public.shapes import (
    ShapeField,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_inputs,
    plan_scan_sources,
    row_source_key,
)
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    NullableTypeDTO,
    StructTypeDTO,
)
from .relations import binding_outputs, projection_sources


@dataclass(frozen=True, slots=True)
class DeclaredPath:
    """One declared member path, in both forms the source step needs."""

    schema_path: str
    logical_path: str


def ordered_projections(blueprint: GraphBlueprint) -> tuple[ProjectionDTO, ...]:
    """Projections in dependency order, each read after what it references."""
    pending = {
        projection.name: projection
        for projection in blueprint.data.projections
    }
    ordered: list[ProjectionDTO] = []
    while pending:
        ready = sorted(
            (
                projection
                for projection in pending.values()
                if not (projection_sources(projection) & pending.keys())
            ),
            key=lambda projection: projection.name,
        )
        if not ready:
            raise ValueError("projection dependency graph contains a cycle")
        for projection in ready:
            ordered.append(projection)
            del pending[projection.name]
    return tuple(ordered)


def ordered_row_source_plans(
    blueprint: GraphBlueprint,
) -> tuple[RowSourcePlanDTO, ...]:
    """Every derived plan once, children before the plans that read them."""
    roots = [
        item.row_source
        for item in blueprint.data.projections
        if item.row_source is not None
    ]
    roots.extend(
        binding.rows
        for binding in blueprint.bindings
        if binding.rows is not None
    )
    ordered: list[RowSourcePlanDTO] = []
    seen: set[str] = set()

    def visit(plan: RowSourcePlanDTO) -> None:
        key = row_source_key(plan)
        if key in seen:
            return
        seen.add(key)
        for child in plan_inputs(plan):
            visit(child)
        if not isinstance(plan, RowScanDTO):
            ordered.append(plan)

    for plan in roots:
        visit(plan)
    return tuple(ordered)


def declaration_fields(
    blueprint: GraphBlueprint,
) -> dict[str, tuple[ShapeField, ...]]:
    """The top-level field shape of every relation and projection a plan scans."""
    fields = {
        item.name: tuple(
            ShapeField(field.name, field.name, field.logical_type)
            for field in item.columns
        )
        for item in blueprint.data.relations
    }
    fields.update({
        item.name: tuple(
            ShapeField(field.name, field.name, field.logical_type)
            for field in item.columns
        )
        for item in blueprint.data.projections
    })
    return fields


def _snake_name(value: str) -> str:
    """The blueprint's logical name for a generated struct class name."""
    text = value.rsplit(".", 1)[-1]
    if text.endswith("Struct"):
        text = text[:-len("Struct")]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def _struct_name(value: StructTypeDTO) -> str:
    return _snake_name(value.qualname)


def _structs(blueprint: GraphBlueprint) -> dict[str, StructDTO]:
    return {struct.name: struct for struct in blueprint.data.structs}


def declared_non_null_paths(
    relation: RelationDTO, structs: Mapping[str, StructDTO],
) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Every path the contract claims is non-null, by logical and schema form."""
    found: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def walk(
        columns: tuple[ColumnDTO, ...],
        prefix: tuple[str, ...],
        schema_prefix: tuple[str, ...],
        parents: frozenset[str],
    ) -> None:
        for declared in columns:
            logical_type = declared.logical_type
            nullable = isinstance(logical_type, NullableTypeDTO)
            base = logical_type.value if nullable else logical_type
            is_array = isinstance(base, ArrayTypeDTO)
            item = base.item if is_array else base
            logical_path = (*prefix, declared.name)
            schema_path = (
                *schema_prefix, declared.name,
                *(PARQUET_LIST_WRAPPER_PATH if is_array else ()),
            )
            if not nullable:
                found.append((logical_path, schema_path))
            if isinstance(item, StructTypeDTO):
                struct_name = _struct_name(item)
                if struct_name not in parents:
                    declaration = structs.get(struct_name)
                    if declaration is not None:
                        walk(
                            declaration.columns, logical_path, schema_path,
                            parents | {struct_name},
                        )

    walk(relation.columns, (), (), frozenset())
    return dict(found)


def declared_read_paths(
    blueprint: GraphBlueprint,
) -> dict[str, tuple[DeclaredPath, ...]]:
    """The non-null-claiming contract paths this build reads, per relation."""
    relations = {
        relation.name: relation for relation in blueprint.data.relations
    }
    structs = _structs(blueprint)
    projections = {
        projection.name: projection
        for projection in blueprint.data.projections
    }
    claims = {
        name: declared_non_null_paths(relation, structs)
        for name, relation in relations.items()
    }
    read: dict[str, set[tuple[str, ...]]] = {
        name: set() for name in relations
    }
    pending: list[Any] = [
        expression
        for binding in blueprint.bindings
        for expression in binding_outputs(binding).values()
    ]
    included: set[str] = set()
    while pending:
        for node in walk_expression_dto(pending.pop()):
            if not isinstance(node, FieldReferenceDTO):
                continue
            if node.source in relations:
                read[node.source].add(node.path)
            elif node.source in projections and node.source not in included:
                included.add(node.source)
                pending.extend(
                    column.expression
                    for column in projections[node.source].columns
                    if column.expression is not None
                )

    def is_read(relation_name: str, claimed: tuple[str, ...]) -> bool:
        """Whether the build reaches one claimed path."""
        return any(
            claimed[:len(seen)] == seen for seen in read[relation_name]
        )

    return {
        relation: tuple(
            DeclaredPath(
                schema_path=".".join(claims[relation][path]),
                logical_path=".".join(path),
            )
            for path in sorted(
                claimed
                for claimed in claims[relation]
                if is_read(relation, claimed)
            )
        )
        for relation in relations
        if any(is_read(relation, claimed) for claimed in claims[relation])
    }


__all__ = [
    "declaration_fields",
    "declared_non_null_paths",
    "declared_read_paths",
    "ordered_projections",
    "ordered_row_source_plans",
]
