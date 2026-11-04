from __future__ import annotations

import unittest

from kg_build_system.distribution.modules.conflict_validation import (
    ConflictReportExecutor,
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
)
from kg_build_system.kernel import (
    Artifact,
    ArtifactPattern,
    ArtifactType,
    ContinuableInput,
    ExecutionContext,
    Input,
    Instruction,
    InstructionKind,
    Key,
    OpeningDirection,
    OpeningId,
    Output,
    Publication,
    ResourceView,
    Step,
    StepId,
    StepStatus,
)

FINDINGS = ArtifactPattern.of("conflict_validation", "findings", "**")
REPORT = ArtifactType.of("conflict_validation", "report")
RECORDS = ArtifactType.of("core", "graph", "node", "Person")


def _instruction(*, fail_on_error: bool) -> Instruction:
    return Instruction(
        InstructionKind("conflict_report", "default"),
        {"fail_on_error": fail_on_error},
    )


def _step() -> Step:
    return Step(
        "conflict_validation",
        "report",
        (
            Input(FINDINGS, Key(("findings",)), "findings"),
            Input(
                ArtifactPattern(RECORDS.key),
                Key(("records", "Person")),
                "Person.records",
            ),
        ),
        (
            Publication(REPORT, Key(("report",))),
            Output(RECORDS, Key(("validated", "Person"))),
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
        runtime_configuration={},
        inputs={
            "findings": (
                ContinuableInput(
                    OpeningId(
                        StepId("conflict_validation", "Person.name"),
                        OpeningDirection.OUTPUT,
                        Key(("findings",)),
                    ),
                    StepStatus.SUCCEEDED,
                    Artifact(
                        Key(("findings",)), ArtifactType.of(
                            "conflict_validation", "findings",
                            "Person", "name",
                        ), findings,
                    ),
                ),
            ),
            "Person.records": (
                ContinuableInput(
                    OpeningId(
                        StepId("core", "aggregate.Person"),
                        OpeningDirection.OUTPUT,
                        Key(("output",)),
                    ),
                    StepStatus.SUCCEEDED,
                    Artifact(Key(("records",)), RECORDS, "relation"),
                ),
            ),
        },
        resources=ResourceView({}),
        logger=None,
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
            [(Key(("validated", "Person")), "relation")],
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
            if artifact.output_name == Key(("report",))
        )
        self.assertEqual(
            report.value, ConflictingNonNullValuesReport((finding,)),
        )
        self.assertIn(
            Key(("validated", "Person")),
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
            [artifact.output_name for artifact in outcome.artifacts],
            [Key(("report",))],
        )


if __name__ == "__main__":
    unittest.main()
