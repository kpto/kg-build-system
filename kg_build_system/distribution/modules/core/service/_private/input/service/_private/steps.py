"""The source steps the input planner authors."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.data.model.internal import (
    RelationDTO,
    SourceDTO,
)
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.distribution.modules.core.service._private.planning.plan import (
    CorePlan,
)
from kg_build_system.kernel import Instruction, InstructionKind, Output, Step
from kg_build_system.kernel.service.internal.types import type_to_document
from .credentials import credential_reference


def _declaration(
    blueprint: GraphBlueprint, name: str,
) -> RelationDTO | None:
    return next(
        (
            item for item in blueprint.data.relations
            if item.name == name
        ),
        None,
    )


def source_payload(
    source: SourceDTO,
    relation: str,
    blueprint: GraphBlueprint,
    read_paths: Mapping[str, tuple[Any, ...]],
) -> dict[str, Any]:
    """The typed payload one source-relation instruction carries."""
    declaration = _declaration(blueprint, source.relation.name)
    return {
        "relation": relation,
        "location": source.location,
        "format": source.format,
        "credential_reference": credential_reference(source),
        "declaration": source.relation.name,
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
            for path in read_paths.get(source.relation.name, ())
            if path.schema_path
        ],
    }


def source_step(
    source: SourceDTO,
    relation: str,
    blueprint: GraphBlueprint,
    read_paths: Mapping[str, tuple[Any, ...]],
) -> Step:
    """One step that opens a physical source as a logical relation."""
    return Step(
        component="core",
        name=f"table.{source.relation.name}",
        inputs=(),
        outputs=(Output(CoreArtifactTypes.table(source.relation.name)),),
        instruction=Instruction(
            InstructionKind("source_relation", "duckdb"),
            source_payload(source, relation, blueprint, read_paths),
        ),
    )


def source_steps(
    blueprint: GraphBlueprint, plan: CorePlan,
) -> tuple[Step, ...]:
    """Every source step, in the plan's source order."""
    return tuple(
        source_step(
            source,
            plan.table_relations[source.relation.name],
            blueprint,
            plan.read_paths,
        )
        for source in plan.sources
    )


__all__ = ["source_payload", "source_step", "source_steps"]
