"""Compilation of the exact-duplicate removal step."""
from __future__ import annotations

from typing import Any

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint
from ......kernel import CompilationContext, ModuleCompiler
from kg_build_system.pipeline.contract.model.public import ContributionDTO, InputDTO, ModuleDefinitionDTO, ModuleReferenceDTO, OutputDTO, StepDTO
from .....model.internal.dto.instruction_dto import InstructionDTO
from ...service.blueprint import blueprint_from_context
from ...service.instructions import python_instruction
from .....model.public.artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)

_RECORDS_INPUT = "records"
_DISTINCT_OUTPUT = "distinct"
_EXECUTOR = (
    "kg_build_system.distribution.service._private.modules.deduplication.executor"
)


class DeduplicationCompiler(ModuleCompiler):
    """Compile one distinct step per bound record component."""

    def __init__(self, configuration: Any, module_class: type[Any]) -> None:
        self.configuration = configuration
        self.module_class = module_class

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        blueprint: GraphBlueprint = blueprint_from_context(context)
        steps: list[StepDTO] = []
        for component in graph_record_components(blueprint):
            records_type = CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )
            name = component.name
            steps.append(StepDTO(
                name=name,
                inputs=(InputDTO(
                    type=records_type, name=None, input_name=_RECORDS_INPUT,
                ),),
                outputs=(OutputDTO(records_type, name=_DISTINCT_OUTPUT),),
                instruction=python_instruction(
                    _EXECUTOR,
                    "execute_instruction",
                    InstructionDTO(
                        kind="deduplication",
                        payload={
                            "component": component.name,
                            "relation": f"kg_distinct_{component.name.lower()}",
                        },
                    ),
                ),
            ))

        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=self.module_class.ID,
                import_module=self.module_class.__module__,
                class_qualname=self.module_class.__qualname__,
                implementation_version=self.module_class.VERSION,
                configuration={},
            )
        )
        return ContributionDTO(definition, tuple(steps))


__all__ = ["DeduplicationCompiler"]
