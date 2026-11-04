"""Compile conflicting-non-null-value findings and report steps."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.kernel import (
    ArtifactType,
    Input,
    Instruction,
    Output,
    PlanContext,
    Publication,
    RuntimeField,
    Step,
)
from ...model.public import ConflictValidationConfiguration
from .artifacts import (
    ComponentDTO,
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)

_RECORDS_INPUT = "records"
_FINDINGS = "findings"
_FINDINGS_PATTERN = "findings.*"
_REPORT_OUTPUT = "report"
_RECORDS_SUFFIX = ".records"
_VALIDATED_SUFFIX = ".validated"


class ConflictValidationPlanner:
    """Plan one findings step per property and one deferred report step."""

    component_id = "conflict_validation"
    version = "2"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, configuration: ConflictValidationConfiguration) -> None:
        self._configuration = configuration

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return findings steps and the deferred report step.

        Example:
            ```python
            steps = ConflictValidationPlanner(
                ConflictValidationConfiguration(),
            ).plan(blueprint, PlanContext())
            ```
        """
        del context
        steps: list[Step] = []
        components = graph_record_components(blueprint)
        for component in components:
            records_type = CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )
            for prop in component.properties:
                name = f"{component.name}.{prop.name}"
                steps.append(Step(
                    component=self.component_id,
                    name=name,
                    inputs=(
                        Input(
                            type=records_type,
                            name=None,
                            input_name=_RECORDS_INPUT,
                        ),
                    ),
                    outputs=(
                        Output(
                            ArtifactType(
                                self.component_id,
                                f"{_FINDINGS}.{name}",
                            ),
                            name=_FINDINGS,
                        ),
                    ),
                    instruction=Instruction(
                        ("conflict_findings", "duckdb"),
                        {
                            "component": component.name,
                            "field": prop.name,
                        },
                    ),
                ))

        steps.append(self._report_step(components))
        return tuple(steps)

    def _report_step(self, components: Sequence[ComponentDTO]) -> Step:
        """The deferred step that gathers findings and passes records on."""
        return Step(
            component=self.component_id,
            name=_REPORT_OUTPUT,
            inputs=(
                Input(
                    type=ArtifactType(
                        self.component_id,
                        _FINDINGS_PATTERN,
                    ),
                    name=None,
                    input_name=_FINDINGS,
                ),
                *(
                    Input(
                        type=CoreArtifactTypes.graph_records(
                            component_kind(component), component.name,
                        ),
                        name=None,
                        input_name=(
                            f"{component.name}{_RECORDS_SUFFIX}"
                        ),
                    )
                    for component in components
                ),
            ),
            outputs=(
                Publication(
                    ArtifactType(self.component_id, _REPORT_OUTPUT),
                    name=_REPORT_OUTPUT,
                ),
                *(
                    Output(
                        CoreArtifactTypes.graph_records(
                            component_kind(component), component.name,
                        ),
                        name=f"{component.name}{_VALIDATED_SUFFIX}",
                    )
                    for component in components
                ),
            ),
            assembly_preference="deferred",
            instruction=Instruction(
                ("conflict_report", "default"),
                {"fail_on_error": self._configuration.fail_on_error},
            ),
        )


__all__ = ["ConflictValidationPlanner"]
