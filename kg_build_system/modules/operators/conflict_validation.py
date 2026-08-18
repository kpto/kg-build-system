"""Validation for conflicting non-null graph property values."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ..._frozen_json import freeze_json, thaw_json
from ...workflow.models import (
    ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference,
    OutputSlot, SingleInputSlot, WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...workflow.interfaces import ModuleExecutor
from ...workflow.models import (
    Artifact,
    CandidatePredicate,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    Failure,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStepDraft,
    WorkflowArtifactRoles,
    role_is,
)
from ..core import CoreArtifactRoles


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
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return _Executor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        steps: list[WorkflowStepDraft] = []
        for component in context.blueprint.components:
            graph_role = CoreArtifactRoles.graph_records(
                component.kind, component.name
            )
            for prop in component.properties:
                input_slot = SingleInputSlot(
                    slot_id=f"{self.ID}::{component.name}.{prop.name}.input"
                )
                output_role = ArtifactRole(
                    namespace=self.ID,
                    name=f"findings.{component.name}.{prop.name}",
                )
                step = WorkflowStep(
                    step_id=f"{self.ID}::{component.name}.{prop.name}",
                    module_id=self.ID,
                    inputs=(input_slot,),
                    outputs=(
                        OutputSlot(
                            slot_id=(
                                f"{self.ID}::{component.name}.{prop.name}.output"
                            ),
                            artifact_role=output_role,
                        ),
                    ),
                    payload=freeze_json({
                        "action": "findings",
                        "component": component.name,
                        "field": prop.name,
                    }),
                )
                steps.append(
                    WorkflowStepDraft(
                        definition=step,
                        candidates={input_slot.slot_id: role_is(graph_role)},
                    )
                )

        report_step = self._report_step(context)
        steps.append(report_step)
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
        return WorkflowContribution(definition, tuple(steps))

    def _report_step(
        self, context: CompilationContext[Any],
    ) -> WorkflowStepDraft:
        finding_slot = CollectionInputSlot(
            slot_id=f"{self.ID}::report.findings"
        )
        record_slots = tuple(
            SingleInputSlot(
                slot_id=f"{self.ID}::report.{component.name}.records"
            )
            for component in context.blueprint.components
        )
        outputs = (
            OutputSlot(
                slot_id=f"{self.ID}::report.output",
                artifact_role=WorkflowArtifactRoles.published(self.ID, "report"),
            ),
            *(
                OutputSlot(
                    slot_id=f"{self.ID}::report.{component.name}.output",
                    artifact_role=CoreArtifactRoles.graph_records(
                        component.kind, component.name
                    ),
                )
                for component in context.blueprint.components
            ),
        )
        step = WorkflowStep(
            step_id=f"{self.ID}::report",
            module_id=self.ID,
            inputs=(finding_slot, *record_slots),
            outputs=outputs,
            payload=freeze_json({
                "action": "report",
                "fail_on_error": self.configuration.fail_on_error,
            }),
        )
        candidates: dict[str, CandidatePredicate] = {
            finding_slot.slot_id: lambda _input, output: (
                output.artifact_role.namespace == self.ID
                and output.artifact_role.name.startswith("findings.")
            )
        }
        for slot, component in zip(
            record_slots, context.blueprint.components, strict=True
        ):
            role = CoreArtifactRoles.graph_records(
                component.kind, component.name
            )
            candidates[slot.slot_id] = role_is(role)
        return WorkflowStepDraft(
            definition=step,
            assembly_preference="deferred",
            candidates=candidates,
        )


class _Executor(ModuleExecutor):
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        payload = thaw_json(context.step.payload)  # type: ignore[arg-type]
        if not isinstance(payload, dict):
            raise ValueError("conflict validation requires an object payload")
        if payload.get("action") == "findings":
            return self._findings(context, payload)
        if payload.get("action") == "report":
            return self._report(context, payload)
        raise ValueError(f"unknown conflict-validation action {payload.get('action')!r}")

    def _findings(
        self, context: ExecutionContext, payload: dict[str, Any],
    ) -> StepOutcome:
        relation = next(
            item.artifact.value
            for contributions in context.inputs.values()
            for item in contributions
            if item.artifact is not None
        )
        field_name = str(payload["field"])
        field = _quote_identifier(field_name)
        source = context.services.relations.reference(relation)
        sql = (
            f'SELECT "build_key", count(DISTINCT "{field}") '
            f"FROM {source} "
            'WHERE "build_key" IS NOT NULL '
            'GROUP BY "build_key" '
            f'HAVING count(DISTINCT "{field}") '
            f'FILTER (WHERE "{field}" IS NOT NULL) > 1'
        )
        findings = tuple(
            ConflictingNonNullValueFinding(
                component=str(payload["component"]),
                build_key=str(key),
                property_name=field_name,
                distinct_values=count,
            )
            for key, count in context.services.relations.query(sql).fetchall()
        )
        output = context.step.outputs[0]
        artifact = Artifact(output.slot_id, output.artifact_role, findings)
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.SUCCEEDED,
            (artifact,),
        )

    def _report(
        self, context: ExecutionContext, payload: dict[str, Any],
    ) -> StepOutcome:
        findings_slot = f"{RejectConflictingNonNullValuesModule.ID}::report.findings"
        findings = tuple(
            finding
            for item in context.inputs[findings_slot]
            if item.artifact is not None
            for finding in item.artifact.value
        )
        record_artifacts: dict[str, Artifact] = {}
        prefix = f"{RejectConflictingNonNullValuesModule.ID}::report."
        suffix = ".records"
        for slot_id, contributions in context.inputs.items():
            if slot_id == findings_slot:
                continue
            artifact = next(
                (
                    item.artifact
                    for item in contributions
                    if item.artifact is not None
                ),
                None,
            )
            if artifact is not None:
                component = slot_id.removeprefix(prefix).removesuffix(suffix)
                record_artifacts[component] = artifact

        forwarded: list[Artifact] = []
        for output in context.step.outputs[1:]:
            identity = CoreArtifactRoles.graph_record_identity(output.artifact_role)
            if identity is None or identity.component not in record_artifacts:
                continue
            forwarded.append(
                Artifact(
                    output.slot_id,
                    output.artifact_role,
                    record_artifacts[identity.component].value,
                )
            )
        if not findings:
            return StepOutcome(
                context.step.step_id,
                context.step.module_id,
                StepStatus.SUCCEEDED,
                tuple(forwarded),
            )

        report = ConflictingNonNullValuesReport(findings)
        report_output = context.step.outputs[0]
        report_artifact = Artifact(
            report_output.slot_id, report_output.artifact_role, report
        )
        if not payload["fail_on_error"]:
            return StepOutcome(
                context.step.step_id,
                context.step.module_id,
                StepStatus.SUCCEEDED,
                (report_artifact, *forwarded),
            )

        failure = Failure(
            message=(
                f"validation found {len(findings)} conflicting non-null value(s)"
            ),
            module_id=context.step.module_id,
            step_id=context.step.step_id,
        )
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.FAILED,
            (report_artifact,),
            failure=failure,
        )

    async def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return await super().handle_disrupted(context)
