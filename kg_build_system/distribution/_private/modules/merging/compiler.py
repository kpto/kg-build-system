"""Compilation of the compatible-facts merging step."""
from __future__ import annotations

from typing import Any

from .....declaration.blueprint.public import GraphBlueprint
from .....kernel import CompilationContext, ModuleCompiler
from .....pipeline.contract.public import (
    ContributionDTO,
    InputDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
    OutputDTO,
    StepDTO,
)
from ....internal.dto.instruction_dto import InstructionDTO
from ...service.blueprint import blueprint_from_context
from ...service.instructions import python_instruction
from ....modules.core.artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)
from ....modules.merging.module import (
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
)
from .configuration import component_name

_RECORDS_INPUT = "records"
_MERGED_OUTPUT = "merged"
_EXECUTOR = "kg_build_system.distribution._private.modules.merging.executor"


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


class MergingCompiler(ModuleCompiler):
    """Compile one merge step per selected record component."""

    def __init__(self, configuration: MergeCompatibleFactsModuleConfiguration) -> None:
        self.configuration = configuration

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        blueprint: GraphBlueprint = blueprint_from_context(context)
        steps: list[StepDTO] = []
        scope = self.configuration.components
        scope_names = None if scope is None else {
            component_name(component) for component in scope
        }
        for component in graph_record_components(blueprint):
            if scope_names is not None and component.name not in scope_names:
                continue
            records_type = CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )
            fields = [prop.name for prop in component.properties]
            if component_kind(component) == "edge":
                fields = ["source_build_key", "target_build_key", *fields]
            aggregates = [
                f'min("{_quote_identifier(name)}") AS "{_quote_identifier(name)}"'
                for name in fields
            ]
            select = ", ".join(['"build_key"', *aggregates])
            steps.append(StepDTO(
                name=component.name,
                inputs=(InputDTO(
                    type=records_type, name=None, input_name=_RECORDS_INPUT,
                ),),
                outputs=(OutputDTO(records_type, name=_MERGED_OUTPUT),),
                instruction=python_instruction(
                    _EXECUTOR,
                    "execute_instruction",
                    InstructionDTO(
                        kind="merging",
                        payload={
                            "relation": f"kg_normalised_{component.name.lower()}",
                            "select": select,
                        },
                    ),
                ),
            ))

        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=MergeCompatibleFactsModule.ID,
                import_module=MergeCompatibleFactsModule.__module__,
                class_qualname=MergeCompatibleFactsModule.__qualname__,
                implementation_version=MergeCompatibleFactsModule.VERSION,
                configuration=self.configuration.to_json(),
            )
        )
        return ContributionDTO(definition, tuple(steps))


__all__ = ["MergingCompiler"]
