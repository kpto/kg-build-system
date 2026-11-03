"""Execution of the conflicting-non-null-value validation steps."""
from __future__ import annotations

from typing import Any

from ....kernel import (
    Artifact,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Failure,
    Output,
    StepOutcome,
    StepStatus,
)
from ...internal.dto.instruction_dto import decode_instruction
from ...internal.service.instructions import nested_instruction
from ...internal.service.runtime import (
    as_mapping,
    execution_services,
    instruction_payload,
    output_name,
    skipped,
)
from .module import (
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
)

_RECORDS_INPUT = "records"
_FINDINGS = "findings"
_REPORT_OUTPUT = "report"


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


def execute_instruction(context: Any, instruction: Any) -> StepOutcome:
    """Run one validation step from a stable Python instruction reference."""
    executor = ConflictValidationExecutor()
    local = nested_instruction(instruction)
    if local.kind == "conflict_findings":
        return executor._findings(context, local.payload, None)
    if local.kind == "conflict_report":
        return executor._report(context, local.payload)
    raise ValueError(
        f"unknown conflict-validation instruction {local.kind!r}"
    )


class ConflictValidationExecutor:
    """Run one findings or report step from its instruction."""

    def handle(
        self, context: ExecutionContext, services: Any = None,
    ) -> StepOutcome:
        services = execution_services(context, services)
        instruction = decode_instruction(instruction_payload(context))
        if instruction.kind == "conflict_findings":
            return self._findings(context, instruction.payload, services)
        if instruction.kind == "conflict_report":
            return self._report(context, instruction.payload)
        raise ValueError(
            f"unknown conflict-validation instruction {instruction.kind!r}"
        )

    def _findings(
        self,
        context: ExecutionContext,
        payload: Any,
        services: Any,
    ) -> StepOutcome:
        instructions = as_mapping(payload, context="conflict findings payload")
        relation = next(
            item.artifact.value
            for item in context.inputs[_RECORDS_INPUT]
            if item.artifact is not None
        )
        field_name = str(instructions["field"])
        field = _quote_identifier(field_name)
        source = services.relations.reference(relation)
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
            for key, count in services.relations.query(sql).fetchall()
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
        self, context: ExecutionContext, payload: Any,
    ) -> StepOutcome:
        instructions = as_mapping(payload, context="conflict report payload")
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
        self, context: DisruptedExecutionContext, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


__all__ = ["ConflictValidationExecutor", "execute_instruction"]
