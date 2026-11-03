"""The steps the core module authors, and the instruction each one runs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint
from kg_build_system.declaration.languages.table.model.internal import ProjectionDTO, RelationDTO, RowSourcePlanDTO
from kg_build_system.declaration.languages.table.service.internal import plan_inputs, row_source_key
from kg_build_system.pipeline.compilation.service.internal.instruction.duckdb import row_source_sql
from kg_build_system.pipeline.contract.model.public import InputDTO, OutputDTO, StepDTO
from .....model.internal.dto.instruction_dto import (
    AggregateInstructionDTO,
    DeclaredPathDTO,
    RelationInstructionDTO,
    SourceRelationInstructionDTO,
)
from ...dto.instruction_codec import encode_declared_column
from ...service.instructions import python_instruction
from .....model.public.artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)
from .relations import (
    binding_sources,
    binding_sql,
    projection_sources,
    projection_sql,
)


_CORE_EXECUTOR = (
    "kg_build_system.distribution.service._private.modules.core.executor"
)
_EXECUTE = "execute_instruction"


def _python(step_name: str, inner: Any) -> Any:
    return python_instruction(_CORE_EXECUTOR, _EXECUTE, inner)


def read_input(
    name: str,
    projection_relations: Mapping[str, str],
    row_source_relations: Mapping[str, str] | None = None,
) -> InputDTO:
    """One opening a projection or binding takes: a relation its SQL reads."""
    if row_source_relations is not None and name in row_source_relations:
        return InputDTO(
            type=CoreArtifactTypes.row_source(name),
            name=None,
            input_name=f"row_source.{name}",
        )
    projection = name in projection_relations
    return InputDTO(
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
    read_paths: Mapping[str, tuple[DeclaredPathDTO, ...]],
) -> StepDTO:
    declaration: RelationDTO | None = next(
        (
            item for item in blueprint.data.relations
            if item.name == source.table
        ),
        None,
    )
    inner = SourceRelationInstructionDTO(
        relation=relation,
        location=source.location,
        format=source.format,
        credential_reference=source.credential_reference,
        declaration=source.table,
        declared_columns=tuple(
            encode_declared_column(column.name, column.logical_type)
            for column in declaration.columns
        ) if declaration is not None else (),
        declared_paths=tuple(
            path for path in read_paths.get(source.table, ())
            if path.schema_path
        ),
    )
    return StepDTO(
        name=f"table.{source.table}",
        inputs=(),
        outputs=(OutputDTO(CoreArtifactTypes.table(source.table)),),
        instruction=_python(f"table.{source.table}", inner),
    )


def row_source_step(
    plan: RowSourcePlanDTO,
    relation: str,
    relations: dict[str, str],
    shapes: Mapping[str, tuple[Any, ...]],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
) -> StepDTO:
    key = row_source_key(plan)
    return StepDTO(
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
        outputs=(OutputDTO(CoreArtifactTypes.row_source(key)),),
        instruction=_python(
            f"rowsource.{key}",
            RelationInstructionDTO(
                relation=relation,
                sql=row_source_sql(plan, relations, shapes),
            ),
        ),
    )


def projection_step(
    blueprint: GraphBlueprint,
    projection: ProjectionDTO,
    relation: str,
    relations: dict[str, str],
    projection_relations: dict[str, str],
    row_source_relations: dict[str, str],
) -> StepDTO:
    return StepDTO(
        name=f"projection.{projection.name}",
        inputs=tuple(
            read_input(name, projection_relations, row_source_relations)
            for name in sorted(projection_sources(projection))
        ),
        outputs=(OutputDTO(CoreArtifactTypes.projection(projection.name)),),
        instruction=_python(
            f"projection.{projection.name}",
            RelationInstructionDTO(
                relation=relation,
                sql=projection_sql(blueprint, relations, projection),
            ),
        ),
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
) -> StepDTO:
    identity = binding_identity(binding, index)
    binding_sql_text = binding_sql(blueprint, relations, binding)
    return StepDTO(
        name=f"binding.{index}",
        inputs=tuple(
            read_input(name, projection_relations, row_source_relations)
            for name in sorted(binding_sources(binding))
        ),
        outputs=(OutputDTO(CoreArtifactTypes.binding(identity)),),
        instruction=_python(
            f"binding.{index}",
            RelationInstructionDTO(
                relation=f"kg_binding_{index}",
                sql=(
                    f"SELECT *, '{identity}' AS _kg_binding_symbol "
                    f"FROM ({binding_sql_text})"
                ),
            ),
        ),
    )


def aggregation_steps(blueprint: GraphBlueprint) -> tuple[StepDTO, ...]:
    steps: list[StepDTO] = []
    for component in graph_record_components(blueprint):
        identities = tuple(
            binding_identity(binding, index)
            for index, binding in enumerate(blueprint.bindings)
            if binding.component == component.name
        )
        if not identities:
            continue
        name = f"aggregate.{component.name}"
        steps.append(StepDTO(
            name=name,
            inputs=tuple(
                InputDTO(
                    type=CoreArtifactTypes.binding(identity),
                    name=None,
                    input_name=f"binding.{identity}",
                )
                for identity in identities
            ),
            outputs=(OutputDTO(CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )),),
            assembly_preference="deferred",
            instruction=_python(
                name,
                AggregateInstructionDTO(
                    relation=f"kg_graph_{component.name.lower()}",
                ),
            ),
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
