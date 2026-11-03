"""Compilation of the meta-graph description step."""
from __future__ import annotations

from typing import Any

from ....kernel import CompilationContext, ModuleCompiler
from ....pipeline.contract.public import (
    ArtifactTypeDTO,
    ContributionDTO,
    InputDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
    PublicationDTO,
    StepDTO,
)
from ...internal.service.blueprint import blueprint_from_context
from .instruction_dto import (
    MetaGraphDocumentDTO,
    encode_meta_graph_instruction,
)
from .module import MetaGraphModule, MetaGraphModuleConfiguration
from .topology import component_entries

_RECORDS_INPUT = "records"
_DOCUMENT_STEP_NAME = "document"


class MetaGraphCompiler(ModuleCompiler):
    """Compile the one deferred document step."""

    def __init__(self, configuration: MetaGraphModuleConfiguration) -> None:
        self.configuration = configuration

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        entries = component_entries(blueprint_from_context(context))
        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=MetaGraphModule.ID,
                import_module=MetaGraphModule.__module__,
                class_qualname=MetaGraphModule.__qualname__,
                implementation_version=MetaGraphModule.VERSION,
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
                    ArtifactTypeDTO(MetaGraphModule.ID, "meta_graph_document"),
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
