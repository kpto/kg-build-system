"""Validation for conflicting non-null graph property values."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ..._frozen_json import freeze_json
from ...workflow.models import (
    Artifact, ArtifactType, DisruptedExecutionContext, ExecutionContext,
    ExecutorFactoryContext, Failure, Input, ModuleDefinition, ModuleReference,
    Output, Publication, StepOutcome, StepStatus, WorkflowContribution,
    WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...topology.ir import ComponentIR as ComponentDefinition
from ...workflow.identity import output_name
from ...workflow.interfaces import ModuleExecutor
from ..core import CoreArtifactTypes, graph_record_components


@dataclass(frozen=True)
class RejectConflictingNonNullValuesConfiguration(ModuleRegistrationConfiguration):
    fail_on_error: bool = True


@dataclass(frozen=True)
class ConflictingNonNullValueFinding:
    component: str
    build_key: str
    property_name: str
    distinct_values: int


@dataclass(frozen=True)
class ConflictingNonNullValuesReport:
    findings: tuple[ConflictingNonNullValueFinding, ...]


_RECORDS_INPUT = "records"
"""What a findings step calls the graph records it reads."""

_FINDINGS = "findings"
"""What a findings step calls what it found, and what the report calls the collection."""

_FINDINGS_PATTERN = "findings.*"
"""The family of findings types the report takes, one port per type it matches."""

_REPORT_OUTPUT = "report"
"""The report step, and the name and type of the publication it writes."""

_RECORDS_SUFFIX = ".records"
"""The opening on the report step one component's records arrive at."""

_VALIDATED_SUFFIX = ".validated"
"""The opening on the report step that component's records leave by."""


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


@dataclass(frozen=True)
class RejectConflictingNonNullValuesModule(Module):
    configuration: RejectConflictingNonNullValuesConfiguration

    ID: ClassVar[str] = "reject_conflicting_non_null_values"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[
        type[RejectConflictingNonNullValuesConfiguration]
    ] = RejectConflictingNonNullValuesConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return _Executor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        steps: list[WorkflowStep] = []
        instructions: dict[str, Any] = {}
        components = graph_record_components(context.blueprint)
        for component in components:
            records_type = CoreArtifactTypes.graph_records(
                component.kind, component.name
            )
            for prop in component.properties:
                name = f"{component.name}.{prop.name}"
                steps.append(WorkflowStep(
                    inputs=(Input(records_type, _RECORDS_INPUT),),
                    outputs=(Output(
                        ArtifactType(namespace=self.ID, name=f"{_FINDINGS}.{name}"),
                        _FINDINGS,
                    ),),
                    name=name,
                ))
                instructions[name] = {
                    "action": "findings",
                    "component": component.name,
                    "field": prop.name,
                }

        steps.append(self._report_step(components))
        instructions[_REPORT_OUTPUT] = {
            "action": "report",
            "fail_on_error": self.configuration.fail_on_error,
        }

        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({
                    "fail_on_error": self.configuration.fail_on_error,
                }),
            )
        )
        return WorkflowContribution(
            definition, tuple(steps), freeze_json({"instructions": instructions}),
        )

    def _report_step(
        self, components: tuple[ComponentDefinition, ...],
    ) -> WorkflowStep:
        """The deferred step that gathers every findings type and passes records on.

        Its findings arrive through one open input, which takes one output of each type the
        findings steps write. Each component's records arrive at an opening named for that
        component, and leave by a matching one of their own, since the type they carry is the
        same one the steps upstream that made them write.
        """
        return WorkflowStep(
            inputs=(
                Input(
                    ArtifactType(namespace=self.ID, name=_FINDINGS_PATTERN),
                    _FINDINGS,
                ),
                *(
                    Input(
                        CoreArtifactTypes.graph_records(
                            component.kind, component.name
                        ),
                        f"{component.name}{_RECORDS_SUFFIX}",
                    )
                    for component in components
                ),
            ),
            outputs=(
                Publication(
                    ArtifactType(namespace=self.ID, name=_REPORT_OUTPUT),
                    _REPORT_OUTPUT,
                ),
                *(
                    Output(
                        CoreArtifactTypes.graph_records(
                            component.kind, component.name
                        ),
                        f"{component.name}{_VALIDATED_SUFFIX}",
                    )
                    for component in components
                ),
            ),
            name=_REPORT_OUTPUT,
            assembly_preference="deferred",
        )


class _Executor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instructions = context.variables["instructions"][context.step.name]
        if not isinstance(instructions, dict):
            raise ValueError("conflict validation requires an object instruction")
        if instructions.get("action") == "findings":
            return self._findings(context, instructions)
        if instructions.get("action") == "report":
            return self._report(context, instructions)
        raise ValueError(
            f"unknown conflict-validation action {instructions.get('action')!r}"
        )

    def _findings(
        self, context: ExecutionContext, instructions: dict[str, Any],
    ) -> StepOutcome:
        relation = next(
            item.artifact.value
            for item in context.inputs[_RECORDS_INPUT]
            if item.artifact is not None
        )
        field_name = str(instructions["field"])
        field = _quote_identifier(field_name)
        source = context.services.relations.reference(relation)
        # No filter on ``build_key``: an operator looking for bad values must not
        # exclude the records most worth reporting. Identity guards upstream mean
        # a null key has already aborted the build; if one ever reaches here it is
        # grouped like any other key rather than discarded in silence.
        sql = (
            f'SELECT "build_key", count(DISTINCT "{field}") '
            f"FROM {source} "
            'GROUP BY "build_key" '
            f'HAVING count(DISTINCT "{field}") '
            f'FILTER (WHERE "{field}" IS NOT NULL) > 1'
        )
        findings = tuple(
            ConflictingNonNullValueFinding(
                component=str(instructions["component"]),
                build_key=str(key),
                property_name=field_name,
                distinct_values=count,
            )
            for key, count in context.services.relations.query(sql).fetchall()
        )
        outputs = {output_name(given): given for given in context.step.outputs}
        artifact = Artifact(_FINDINGS, outputs[_FINDINGS].type, findings)
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    def _report(
        self, context: ExecutionContext, instructions: dict[str, Any],
    ) -> StepOutcome:
        findings = tuple(
            finding
            for item in context.inputs[_FINDINGS]
            if item.artifact is not None
            for finding in item.artifact.value
        )
        records: dict[ArtifactType, Any] = {}
        for input_name, contributions in context.inputs.items():
            if input_name == _FINDINGS:
                continue
            for item in contributions:
                if item.artifact is not None:
                    records[item.artifact.type] = item.artifact.value

        outputs = {output_name(given): given for given in context.step.outputs}
        forwarded = tuple(
            Artifact(name, given.type, records[given.type])
            for name, given in outputs.items()
            if isinstance(given, Output) and given.type in records
        )
        if not findings:
            return StepOutcome(
                step_id=context.step_id,
                module_id=context.module_id,
                status=StepStatus.SUCCEEDED,
                artifacts=forwarded,
            )

        report = ConflictingNonNullValuesReport(findings)
        report_artifact = Artifact(
            _REPORT_OUTPUT, outputs[_REPORT_OUTPUT].type, report,
        )
        if not instructions["fail_on_error"]:
            return StepOutcome(
                step_id=context.step_id,
                module_id=context.module_id,
                status=StepStatus.SUCCEEDED,
                artifacts=(report_artifact, *forwarded),
            )

        failure = Failure(
            message=(
                f"validation found {len(findings)} conflicting non-null value(s)"
            ),
            module_id=context.module_id,
            step_id=context.step_id,
        )
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.FAILED,
            artifacts=(report_artifact,),
            failure=failure,
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
