"""Execute the conflict-report step."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Failure,
    Instruction,
    InstructionKind,
    Key,
    Output,
    StepOutcome,
    StepStatus,
)

from ....runtime import (
    instruction_payload,
    output_name,
    skipped,
)
from ...model.public import (
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
)

_FINDINGS = "findings"
_REPORT_OUTPUT = Key(("report",))


class ConflictReportExecutor:
    """Gather findings, publish the report and forward the graph records."""

    kinds = (InstructionKind("conflict_report", "default"),)
    resources = ()

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Publish findings when present and decide whether they fail the run.

        Example:
            ```python
            outcome = ConflictReportExecutor().execute(context, instruction)
            ```
        """
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        return self._report(context, instruction_payload(instruction))

    def _report(
        self,
        context: ExecutionContext,
        payload: Mapping[str, Any],
    ) -> StepOutcome:
        findings = tuple(
            finding
            for item in context.inputs.get(_FINDINGS, ())
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
                status=StepStatus.SUCCEEDED,
                artifacts=forwarded,
            )

        report = ConflictingNonNullValuesReport(findings)
        report_artifact = Artifact(
            _REPORT_OUTPUT, outputs[_REPORT_OUTPUT].type, report,
        )
        if not payload["fail_on_error"]:
            return StepOutcome(
                step_id=context.step_id,
                status=StepStatus.SUCCEEDED,
                artifacts=(report_artifact, *forwarded),
            )

        failure = Failure(
            message=(
                f"validation found {len(findings)} conflicting non-null value(s)"
            ),
            step_id=context.step_id,
        )
        return StepOutcome(
            step_id=context.step_id,
            status=StepStatus.FAILED,
            artifacts=(report_artifact,),
            failure=failure,
        )


__all__ = ["ConflictReportExecutor"]
