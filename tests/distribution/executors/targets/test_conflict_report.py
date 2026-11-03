from __future__ import annotations

import unittest

from kg_build_system.distribution.executors.conflict_validation import (
    ConflictReportExecutor,
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
)
from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    ContinuableInput,
    ExecutionContext,
    Input,
    Instruction,
    Output,
    Publication,
    Step,
    StepStatus,
)

FINDINGS = ArtifactType("conflict_validation", "findings.*")
REPORT = ArtifactType("conflict_validation", "report")
RECORDS = ArtifactType("core", "graph.node.Person")


def _instruction(*, fail_on_error: bool) -> Instruction:
    return Instruction(
        ("conflict_report", "default"),
        {"fail_on_error": fail_on_error},
    )


def _step() -> Step:
    return Step(
        "conflict_validation",
        "report",
        (
            Input(FINDINGS, None, "findings"),
            Input(RECORDS, None, "Person.records"),
        ),
        (
            Publication(REPORT, "report"),
            Output(RECORDS, "Person.validated"),
        ),
        _instruction(fail_on_error=True),
        assembly_preference="deferred",
    )


def _context(
    findings: tuple[ConflictingNonNullValueFinding, ...],
) -> ExecutionContext:
    step = _step()
    return ExecutionContext(
        step=step,
        step_id="conflict_validation.report",
        component=step.component,
        runtime_configuration={},
        inputs={
            "findings": (
                ContinuableInput(
                    "conflict_validation.findings.report",
                    StepStatus.SUCCEEDED,
                    Artifact("findings", FINDINGS, findings),
                ),
            ),
            "Person.records": (
                ContinuableInput(
                    "core.records.records",
                    StepStatus.SUCCEEDED,
                    Artifact("Person.records", RECORDS, "relation"),
                ),
            ),
        },
        services=None,
    )


class ConflictReportExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = ConflictReportExecutor()

    def test_no_findings_succeeds_and_forwards_the_records(self) -> None:
        context = _context(())
        instruction = _instruction(fail_on_error=True)

        outcome = self.executor.execute(context, instruction)

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(
            [(artifact.output_name, artifact.value) for artifact in outcome.artifacts],
            [("Person.validated", "relation")],
        )

    def test_findings_are_reported_when_failure_is_disabled(self) -> None:
        finding = ConflictingNonNullValueFinding(
            "Person", "person-1", "name", 2,
        )
        context = _context((finding,))
        instruction = _instruction(fail_on_error=False)

        outcome = self.executor.execute(context, instruction)

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertIsNone(outcome.failure)
        report = next(
            artifact for artifact in outcome.artifacts
            if artifact.output_name == "report"
        )
        self.assertEqual(
            report.value, ConflictingNonNullValuesReport((finding,)),
        )
        self.assertIn(
            "Person.validated",
            {artifact.output_name for artifact in outcome.artifacts},
        )

    def test_findings_fail_the_run_when_failure_is_enabled(self) -> None:
        finding = ConflictingNonNullValueFinding(
            "Person", "person-1", "name", 2,
        )
        context = _context((finding,))
        instruction = _instruction(fail_on_error=True)

        outcome = self.executor.execute(context, instruction)

        self.assertEqual(outcome.status, StepStatus.FAILED)
        self.assertIsNotNone(outcome.failure)
        assert outcome.failure is not None
        self.assertIn("conflicting non-null", outcome.failure.message)
        self.assertEqual(
            [artifact.output_name for artifact in outcome.artifacts], ["report"],
        )


if __name__ == "__main__":
    unittest.main()
