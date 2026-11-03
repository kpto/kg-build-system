"""Compilation of the Neo4j import-bundle steps."""
from __future__ import annotations

from typing import Any

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint
from ......kernel import CompilationContext, ModuleCompiler
from kg_build_system.pipeline.contract.model.public import ArtifactTypeDTO, ContributionDTO, InputDTO, ModuleDefinitionDTO, ModuleReferenceDTO, OutputDTO, PublicationDTO, RuntimeFieldDTO, StepDTO
from ...service.blueprint import blueprint_from_context
from .....model.public.artifacts import (
    CoreArtifactTypes,
    graph_record_components,
)
from .....model.public.modules.neo4j import Neo4jModuleConfiguration
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

_RECORDS_INPUT = "records"
_COMPONENTS_INPUT = "components"
_SCRIPT_STEP_NAME = "script"


class Neo4jCompiler(ModuleCompiler):
    """Compile one export step per component and one deferred script step."""

    def __init__(
        self,
        configuration: Neo4jModuleConfiguration,
        module_class: type[Any],
    ) -> None:
        self.configuration = configuration
        self.module_class = module_class

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        blueprint: GraphBlueprint = blueprint_from_context(context)
        components = component_imports(graph_record_components(blueprint))
        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=self.module_class.ID,
                import_module=self.module_class.__module__,
                class_qualname=self.module_class.__qualname__,
                implementation_version=self.module_class.VERSION,
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
                    type=ArtifactTypeDTO(self.module_class.ID, "component.*"),
                    name=None,
                    input_name=_COMPONENTS_INPUT,
                ),
            ),
            outputs=(
                PublicationDTO(
                    ArtifactTypeDTO(self.module_class.ID, "import_bundle"),
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
