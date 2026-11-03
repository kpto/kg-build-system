"""Compilation of the Neo4j import-bundle steps."""
from __future__ import annotations

from typing import Any

from ....declaration.blueprint.public import GraphBlueprint
from ....kernel import CompilationContext, ModuleCompiler
from ....pipeline.contract.public import (
    ArtifactTypeDTO,
    ContributionDTO,
    InputDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
    OutputDTO,
    PublicationDTO,
    RuntimeFieldDTO,
    StepDTO,
)
from ...internal.service.blueprint import blueprint_from_context
from ..core.artifacts import CoreArtifactTypes, graph_record_components
from .export import (
    component_export_type,
    component_imports,
    component_step_name,
)
from .instruction_dto import (
    Neo4jComponentImportDTO,
    Neo4jExportInstructionDTO,
    Neo4jScriptInstructionDTO,
    encode_neo4j_instruction,
)
from .module import Neo4jModule, Neo4jModuleConfiguration

_RECORDS_INPUT = "records"
_COMPONENTS_INPUT = "components"
_SCRIPT_STEP_NAME = "script"


class Neo4jCompiler(ModuleCompiler):
    """Compile one export step per component and one deferred script step."""

    def __init__(self, configuration: Neo4jModuleConfiguration) -> None:
        self.configuration = configuration

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        blueprint: GraphBlueprint = blueprint_from_context(context)
        components = component_imports(graph_record_components(blueprint))
        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=Neo4jModule.ID,
                import_module=Neo4jModule.__module__,
                class_qualname=Neo4jModule.__qualname__,
                implementation_version=Neo4jModule.VERSION,
                configuration={
                    "default_database": self.configuration.default_database,
                    "relative_directory": self.configuration.relative_directory,
                    "script_name": self.configuration.script_name,
                },
            ),
            runtime_fields=(RuntimeFieldDTO(
                key="relative_directory",
                description=(
                    "Optional runtime replacement for the Neo4j import-bundle "
                    "directory."
                ),
                required=False,
            ),),
        )
        exports = tuple(
            self._component_export_step(component) for component in components
        )
        script = StepDTO(
            name=_SCRIPT_STEP_NAME,
            inputs=(
                InputDTO(
                    type=ArtifactTypeDTO(Neo4jModule.ID, "component.*"),
                    name=None,
                    input_name=_COMPONENTS_INPUT,
                ),
            ),
            outputs=(
                PublicationDTO(
                    ArtifactTypeDTO(Neo4jModule.ID, "import_bundle"),
                    name="result",
                ),
            ),
            assembly_preference="deferred",
            instruction=encode_neo4j_instruction(Neo4jScriptInstructionDTO(
                components=components,
                script_name=self.configuration.script_name,
                default_database=self.configuration.default_database,
            )),
        )
        return ContributionDTO(definition, (*exports, script))

    @staticmethod
    def _component_export_step(
        component: Neo4jComponentImportDTO,
    ) -> StepDTO:
        return StepDTO(
            name=component_step_name(component),
            inputs=(InputDTO(
                type=CoreArtifactTypes.graph_records(
                    component.kind, component.component,
                ),
                name=None,
                input_name=_RECORDS_INPUT,
            ),),
            outputs=(
                OutputDTO(component_export_type(component), name="result"),
            ),
            assembly_preference="deferred",
            instruction=encode_neo4j_instruction(
                Neo4jExportInstructionDTO(component=component),
            ),
        )


__all__ = ["Neo4jCompiler"]
