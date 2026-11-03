"""Compilation of the meta-graph description step."""
from __future__ import annotations

from typing import Any

from ......kernel import CompilationContext, ModuleCompiler
from kg_build_system.pipeline.contract.model.public import ArtifactTypeDTO, ContributionDTO, InputDTO, ModuleDefinitionDTO, ModuleReferenceDTO, PublicationDTO, StepDTO
from ...service.blueprint import blueprint_from_context
from .....model.public.modules.meta_graph import MetaGraphModuleConfiguration
from .instruction_dto import (
    MetaGraphDocumentDTO,
    encode_meta_graph_instruction,
)
from .topology import component_entries

_RECORDS_INPUT = "records"
_DOCUMENT_STEP_NAME = "document"


class MetaGraphCompiler(ModuleCompiler):
    """Compile the one deferred document step."""

    def __init__(
        self,
        configuration: MetaGraphModuleConfiguration,
        module_class: type[Any],
    ) -> None:
        self.configuration = configuration
        self.module_class = module_class

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        entries = component_entries(blueprint_from_context(context))
        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=self.module_class.ID,
                import_module=self.module_class.__module__,
                class_qualname=self.module_class.__qualname__,
                implementation_version=self.module_class.VERSION,
                configuration={
                    "relative_path": self.configuration.relative_path,
                },
            ),
        )
        step = StepDTO(
            name=_DOCUMENT_STEP_NAME,
            inputs=(InputDTO(
                type=ArtifactTypeDTO("core", "graph.*"),
                name=None,
                input_name=_RECORDS_INPUT,
            ),),
            outputs=(
                PublicationDTO(
                    ArtifactTypeDTO(self.module_class.ID, "meta_graph_document"),
                    name="result",
                ),
            ),
            assembly_preference="deferred",
            instruction=encode_meta_graph_instruction(MetaGraphDocumentDTO(
                relative_path=self.configuration.relative_path,
                example_limit=self.configuration.example_limit,
                include_html=self.configuration.include_html,
                html_relative_path=self.configuration.html_relative_path,
                components=entries,
            )),
        )
        return ContributionDTO(definition, (step,))


__all__ = ["MetaGraphCompiler"]
