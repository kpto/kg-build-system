"""The steps the core planner authors, and the instruction each one runs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.executors.duckdb.service.internal.emitters import (
    DuckDbSqlEmitter,
)
from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.data.model.internal import (
    ProjectionDTO,
    RelationDTO,
    RowSourcePlanDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_inputs,
    row_source_key,
)
from kg_build_system.kernel import (
    ArtifactType,
    Input,
    Instruction,
    Output,
    Step,
)
from kg_build_system.kernel.service.internal.types import type_to_document
from .artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)
from .relations import (
    binding_sources,
    binding_sql,
    projection_sources,
    projection_sql,
    row_source_sql,
)


def _source_payload(
    source: Any,
    relation: str,
    blueprint: GraphBlueprint,
    read_paths: Mapping[str, tuple[Any, ...]],
) -> dict[str, Any]:
    declaration: RelationDTO | None = next(
        (
            item for item in blueprint.data.relations
            if item.name == source.table
        ),
        None,
    )
    return {
        "relation": relation,
        "location": source.location,
        "format": source.format,
        "credential_reference": source.credential_reference,
        "declaration": source.table,
        "declared_columns": [
            {
                "name": column.name,
                "logical_type": type_to_document(column.logical_type),
            }
            for column in (declaration.columns if declaration is not None else ())
        ],
        "declared_paths": [
            {
                "schema_path": path.schema_path,
                "logical_path": path.logical_path,
            }
            for path in read_paths.get(source.table, ())
            if path.schema_path
        ],
    }


def read_input(
    name: str,
    projection_relations: Mapping[str, str],
    row_source_relations: Mapping[str, str] | None = None,
) -> Input:
    """One opening a projection or binding takes: a relation its SQL reads."""
    if row_source_relations is not None and name in row_source_relations:
        return Input(
            type=CoreArtifactTypes.row_source(name),
            name=None,
            input_name=f"row_source.{name}",
        )
    projection = name in projection_relations
    return Input(
        type=(
            CoreArtifactTypes.projection(name) if projection
            else CoreArtifactTypes.table(name)
        ),
        name=None,
        input_name=f"{'projection' if projection else 'table'}.{name}",
    )


def source_step(
    source: Any,
    relation: str,
    blueprint: GraphBlueprint,
    read_paths: Mapping[str, tuple[Any, ...]],
) -> Step:
    return Step(
        component="core",
        name=f"table.{source.table}",
        inputs=(),
        outputs=(Output(CoreArtifactTypes.table(source.table)),),
        instruction=Instruction(
            ("source_relation", "duckdb"),
            _source_payload(source, relation, blueprint, read_paths),
        ),
    )


def row_source_step(
    plan: RowSourcePlanDTO,
    relation: str,
    relations: dict[str, str],
    shapes: Mapping[str, tuple[Any, ...]],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> Step:
    key = row_source_key(plan)
    return Step(
        component="core",
        name=f"rowsource.{key}",
        inputs=tuple(
            read_input(
                child_key,
                projection_relations,
                row_source_relations,
            )
            for child_key in dict.fromkeys(
                row_source_key(child) for child in plan_inputs(plan)
            )
        ),
        outputs=(Output(CoreArtifactTypes.row_source(key)),),
        instruction=Instruction(("sql", "duckdb"), {
            "relation": relation,
            "sql": row_source_sql(plan, relations, shapes, engine=engine),
        }),
    )


def projection_step(
    blueprint: GraphBlueprint,
    projection: ProjectionDTO,
    relation: str,
    relations: dict[str, str],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> Step:
    return Step(
        component="core",
        name=f"projection.{projection.name}",
        inputs=tuple(
            read_input(name, projection_relations, row_source_relations)
            for name in sorted(projection_sources(projection))
        ),
        outputs=(Output(CoreArtifactTypes.projection(projection.name)),),
        instruction=Instruction(("sql", "duckdb"), {
            "relation": relation,
            "sql": projection_sql(
                blueprint, relations, projection, engine=engine,
            ),
        }),
    )


def binding_identity(binding: Any, index: int) -> str:
    """The graph-name identity of one binding in a contribution."""
    return f"{binding.component}.{index}"


def binding_step(
    blueprint: GraphBlueprint,
    binding: Any,
    index: int,
    relations: dict[str, str],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> Step:
    identity = binding_identity(binding, index)
    binding_sql_text = binding_sql(
        blueprint, relations, binding, engine=engine,
    )
    return Step(
        component="core",
        name=f"binding.{index}",
        inputs=tuple(
            read_input(name, projection_relations, row_source_relations)
            for name in sorted(binding_sources(binding))
        ),
        outputs=(Output(CoreArtifactTypes.binding(identity)),),
        instruction=Instruction(("sql", "duckdb"), {
            "relation": f"kg_binding_{index}",
            "sql": (
                f"SELECT *, '{identity}' AS _kg_binding_symbol "
                f"FROM ({binding_sql_text})"
            ),
        }),
    )


def aggregation_steps(blueprint: GraphBlueprint) -> tuple[Step, ...]:
    steps: list[Step] = []
    for component in graph_record_components(blueprint):
        identities = tuple(
            binding_identity(binding, index)
            for index, binding in enumerate(blueprint.bindings)
            if binding.component == component.name
        )
        if not identities:
            continue
        name = f"aggregate.{component.name}"
        steps.append(Step(
            component="core",
            name=name,
            inputs=tuple(
                Input(
                    type=CoreArtifactTypes.binding(identity),
                    name=None,
                    input_name=f"binding.{identity}",
                )
                for identity in identities
            ),
            outputs=(Output(CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )),),
            assembly_preference="deferred",
            instruction=Instruction(("aggregate", "duckdb"), {
                "relation": f"kg_graph_{component.name.lower()}",
            }),
        ))
    return tuple(steps)


__all__ = [
    "aggregation_steps",
    "binding_identity",
    "binding_step",
    "projection_step",
    "read_input",
    "row_source_step",
    "source_step",
]
