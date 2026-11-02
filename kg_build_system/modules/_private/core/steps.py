"""The steps the core module authors, and the instruction each one runs.

A step name is both the step's name among core's steps and the key its
instruction is filed under in the module's variables, so the two are authored
together.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from ...._frozen_json import FrozenJson
from ....compile.internal.ir import BuildBlueprint
from ....engines.internal import DEFAULT_ENGINE, DuckDBEngine
from ....kernel import Input, Output, WorkflowStep
from ....table.internal import (
    plan_inputs,
    row_source_key,
)
from ....table.internal.ir import ProjectionIR
from .artifacts import CoreArtifactTypes, graph_record_components
from .ir import (
    AggregateInstructionIR,
    DeclaredPathIR,
    RelationInstructionIR,
    SourceRelationInstructionIR,
    encode_core_instruction,
    encode_declared_column,
)
from .lowering import (
    binding_sources,
    lower_binding_sql,
    lower_projection_sql,
    projection_sources,
)


@dataclass(frozen=True, slots=True)
class AuthoredStep:
    name: str
    instruction: FrozenJson
    inputs: tuple[Input, ...] = ()
    outputs: tuple[Output, ...] = ()
    assembly_preference: Literal["eager", "deferred"] = "eager"

    def workflow_step(self) -> WorkflowStep:
        return WorkflowStep(
            inputs=self.inputs,
            outputs=self.outputs,
            name=self.name,
            assembly_preference=self.assembly_preference,
        )


def read_input(
    name: str,
    projection_relations: Mapping[str, str],
    row_source_relations: Mapping[str, str] | None = None,
) -> Input:
    """One opening a projection or binding takes: a relation its SQL reads."""
    if row_source_relations is not None and name in row_source_relations:
        return Input(
            type=CoreArtifactTypes.row_source(name),
            name=f"row_source.{name}",
        )
    projection = name in projection_relations
    return Input(
        type=(
            CoreArtifactTypes.projection(name) if projection
            else CoreArtifactTypes.table(name)
        ),
        name=f"{'projection' if projection else 'table'}.{name}",
    )


def source_step(
    source: Any,
    relation: str,
    blueprint: BuildBlueprint,
    read_paths: Mapping[str, tuple[DeclaredPathIR, ...]],
) -> AuthoredStep:
    table = next(
        (item for item in blueprint.tables if item.name == source.table), None,
    )
    return AuthoredStep(
        name=f"table.{source.table}",
        outputs=(Output(CoreArtifactTypes.table(source.table)),),
        instruction=encode_core_instruction(SourceRelationInstructionIR(
            relation=relation,
            location=source.location,
            format=source.format,
            credential_reference=source.credential_reference,
            declaration=source.table,
            declared_columns=tuple(
                encode_declared_column(field.name, field.logical_type)
                for field in table.fields
            ) if table is not None else (),
            declared_paths=tuple(
                path for path in read_paths.get(source.table, ())
                if path.schema_path
            ),
        )),
    )


def row_source_step(
    plan: Any,
    relation: str,
    relations: dict[str, str],
    shapes: Mapping[str, tuple[Any, ...]],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
    *, engine: DuckDBEngine = DEFAULT_ENGINE,
) -> AuthoredStep:
    key = row_source_key(plan)
    return AuthoredStep(
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
        instruction=encode_core_instruction(RelationInstructionIR(
            relation=relation,
            sql=engine.lower_row_source_sql(plan, relations, shapes),
        )),
    )


def projection_step(
    blueprint: BuildBlueprint,
    projection: ProjectionIR,
    relation: str,
    relations: dict[str, str],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
    *, engine: DuckDBEngine = DEFAULT_ENGINE,
) -> AuthoredStep:
    return AuthoredStep(
        name=f"projection.{projection.name}",
        inputs=tuple(
            read_input(name, projection_relations, row_source_relations)
            for name in sorted(projection_sources(projection))
        ),
        outputs=(Output(CoreArtifactTypes.projection(projection.name)),),
        instruction=encode_core_instruction(RelationInstructionIR(
            relation=relation,
            sql=lower_projection_sql(blueprint, relations, projection, engine=engine),
        )),
    )


def binding_step(
    blueprint: BuildBlueprint,
    binding: Any,
    index: int,
    relations: dict[str, str],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
    *, engine: DuckDBEngine = DEFAULT_ENGINE,
) -> AuthoredStep:
    binding_sql = lower_binding_sql(blueprint, relations, binding, engine=engine)
    return AuthoredStep(
        name=f"binding.{index}",
        inputs=tuple(
            read_input(name, projection_relations, row_source_relations)
            for name in sorted(binding_sources(binding))
        ),
        outputs=(Output(CoreArtifactTypes.binding(binding.symbol_id)),),
        instruction=encode_core_instruction(RelationInstructionIR(
            relation=f"kg_binding_{index}",
            sql=(
                f"SELECT *, '{binding.symbol_id}' AS _kg_binding_symbol "
                f"FROM ({binding_sql})"
            ),
        )),
    )


def aggregation_steps(blueprint: BuildBlueprint) -> tuple[AuthoredStep, ...]:
    steps: list[AuthoredStep] = []
    for component in graph_record_components(blueprint):
        symbol_ids = tuple(
            binding.symbol_id
            for binding in blueprint.bindings
            if binding.component == component.name
        )
        if not symbol_ids:
            continue
        steps.append(AuthoredStep(
            name=f"aggregate.{component.name}",
            inputs=tuple(
                Input(
                    type=CoreArtifactTypes.binding(symbol_id),
                    name=f"binding.{symbol_id}",
                )
                for symbol_id in symbol_ids
            ),
            outputs=(Output(CoreArtifactTypes.graph_records(
                component.kind, component.name,
            )),),
            assembly_preference="deferred",
            instruction=encode_core_instruction(AggregateInstructionIR(
                relation=f"kg_graph_{component.name.lower()}",
            )),
        ))
    return tuple(steps)


__all__ = [
    "AuthoredStep",
    "aggregation_steps",
    "binding_step",
    "projection_step",
    "read_input",
    "row_source_step",
    "source_step",
]
