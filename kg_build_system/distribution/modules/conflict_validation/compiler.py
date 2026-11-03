"""Compilation of the conflicting-non-null-value validation steps."""
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
    StepDTO,
)
from ...internal.dto.instruction_dto import InstructionDTO
from ...internal.service.instructions import python_instruction
from ..core.artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)
from ..core.plan import blueprint_from_context
from .module import (
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)

_RECORDS_INPUT = "records"
_FINDINGS = "findings"
_FINDINGS_PATTERN = "findings.*"
_REPORT_OUTPUT = "report"
_RECORDS_SUFFIX = ".records"
_VALIDATED_SUFFIX = ".validated"
_EXECUTOR = "kg_build_system.distribution.modules.conflict_validation.executor"


class ConflictValidationCompiler(ModuleCompiler):
    """Compile one findings step per property and one deferred report step."""

    def __init__(
        self, configuration: RejectConflictingNonNullValuesConfiguration,
    ) -> None:
        self.configuration = configuration

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        blueprint: GraphBlueprint = blueprint_from_context(context)
        steps: list[StepDTO] = []
        components = graph_record_components(blueprint)
        for component in components:
            records_type = CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )
            for prop in component.properties:
                name = f"{component.name}.{prop.name}"
                steps.append(StepDTO(
                    name=name,
                    inputs=(InputDTO(
                        type=records_type, name=None, input_name=_RECORDS_INPUT,
                    ),),
                    outputs=(OutputDTO(
                        ArtifactTypeDTO(
                            namespace=RejectConflictingNonNullValuesModule.ID,
                            name=f"{_FINDINGS}.{name}",
                        ),
                        name=_FINDINGS,
                    ),),
                    instruction=python_instruction(
                        _EXECUTOR,
                        "execute_instruction",
                        InstructionDTO(
                            kind="conflict_findings",
                            payload={
                                "component": component.name,
                                "field": prop.name,
                            },
                        ),
                    ),
                ))

        steps.append(self._report_step(components))

        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=RejectConflictingNonNullValuesModule.ID,
                import_module=RejectConflictingNonNullValuesModule.__module__,
                class_qualname=RejectConflictingNonNullValuesModule.__qualname__,
                implementation_version=RejectConflictingNonNullValuesModule.VERSION,
                configuration={
                    "fail_on_error": self.configuration.fail_on_error,
                },
            )
        )
        return ContributionDTO(definition, tuple(steps))

    def _report_step(self, components: Any) -> StepDTO:
        """The deferred step that gathers findings and passes records on."""
        return StepDTO(
            name=_REPORT_OUTPUT,
            inputs=(
                InputDTO(
                    type=ArtifactTypeDTO(
                        namespace=RejectConflictingNonNullValuesModule.ID,
                        name=_FINDINGS_PATTERN,
                    ),
                    name=None,
                    input_name=_FINDINGS,
                ),
                *(
                    InputDTO(
                        type=CoreArtifactTypes.graph_records(
                            component_kind(component), component.name,
                        ),
                        name=None,
                        input_name=f"{component.name}{_RECORDS_SUFFIX}",
                    )
                    for component in components
                ),
            ),
            outputs=(
                PublicationDTO(
                    type=ArtifactTypeDTO(
                        namespace=RejectConflictingNonNullValuesModule.ID,
                        name=_REPORT_OUTPUT,
                    ),
                    name=_REPORT_OUTPUT,
                ),
                *(
                    OutputDTO(
                        type=CoreArtifactTypes.graph_records(
                            component_kind(component), component.name,
                        ),
                        name=f"{component.name}{_VALIDATED_SUFFIX}",
                    )
                    for component in components
                ),
            ),
            assembly_preference="deferred",
            instruction=python_instruction(
                _EXECUTOR,
                "execute_instruction",
                InstructionDTO(
                    kind="conflict_report",
                    payload={"fail_on_error": self.configuration.fail_on_error},
                ),
            ),
        )


__all__ = ["ConflictValidationCompiler"]
