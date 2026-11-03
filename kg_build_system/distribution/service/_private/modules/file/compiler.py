"""Compilation of the JSON Lines file target."""
from __future__ import annotations

from typing import Any

from ......kernel import CompilationContext, ModuleCompiler
from kg_build_system.pipeline.contract.model.public import ArtifactTypeDTO, ContributionDTO, InputDTO, InstructionDTO, ModuleDefinitionDTO, ModuleReferenceDTO, PublicationDTO, RuntimeFieldDTO, StepDTO
from .....model.public.modules.file import FileModuleConfiguration

_RECORDS_INPUT = "records"


class FileCompiler(ModuleCompiler):
    """Compile the one deferred file-write step."""

    def __init__(
        self, configuration: FileModuleConfiguration, module_class: type[Any],
    ) -> None:
        self.configuration = configuration
        self.module_class = module_class

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        step = StepDTO(
            name="write",
            inputs=(InputDTO(
                type=ArtifactTypeDTO("core", "graph.*"),
                name=None,
                input_name=_RECORDS_INPUT,
            ),),
            outputs=(
                PublicationDTO(
                    ArtifactTypeDTO(self.module_class.ID, "write_result"),
                    name="result",
                ),
            ),
            assembly_preference="deferred",
            instruction=InstructionDTO(
                kind="file",
                payload={"relative_path": self.configuration.relative_path},
            ),
        )
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
            runtime_fields=(
                RuntimeFieldDTO(
                    key="relative_path",
                    description=(
                        "Optional runtime replacement for the relative output path."
                    ),
                    required=False,
                ),
            ),
        )
        return ContributionDTO(definition, (step,))


__all__ = ["FileCompiler"]
