from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system.distribution.modules.duckdb import (
    DuckDbExecutor,
    DuckDbResourceProvider,
    DuckDbService,
)
from kg_build_system.distribution.modules.runtime import RuntimeResources
from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    ContinuableInput,
    DisruptedExecutionContext,
    ExecutionContext,
    Input,
    Instruction,
    InstructionKind,
    Key,
    OpeningDirection,
    OpeningId,
    Output,
    ResourceView,
    RuntimeConfiguration,
    Step,
    StepId,
    StepStatus,
)

RECORDS = ArtifactType.of("core", "records")
RESULT = ArtifactType.of("core", "result")


def _step(
    name: str,
    instruction: Instruction,
    *,
    inputs: tuple[Input, ...] = (),
    output_type: ArtifactType = RESULT,
) -> Step:
    return Step(
        "core",
        name,
        inputs,
        (Output(output_type, Key(("value",))),),
        instruction,
    )


def _context(
    step: Step,
    resources: ResourceView,
    inputs: dict[str, tuple[ContinuableInput, ...]] | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        step=step,
        runtime_configuration={},
        inputs=inputs or {},
        resources=resources,
        logger=None,
    )


def _artifact(name: str, value: object) -> ContinuableInput:
    return ContinuableInput(
        OpeningId(
            StepId("core", "source"),
            OpeningDirection.OUTPUT,
            Key((name,)),
        ),
        StepStatus.SUCCEEDED,
        Artifact(Key((name,)), RECORDS, value),
    )


class DuckDbExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        root = Path(self._temporary.name)
        configuration = RuntimeConfiguration(
            output_directory=root / "output",
            working_directory=root / "working",
            temporary_directory=root / "temporary",
        )
        self.provider = DuckDbResourceProvider()
        self.runtime_resources = RuntimeResources()
        provided = {
            **self.runtime_resources.resources(configuration),
            **self.provider.resources(configuration),
        }
        self.addCleanup(self.provider.close)
        self.addCleanup(self.runtime_resources.close)
        self.resources = ResourceView(provided)
        self.service = self.resources.get(DuckDbService)
        self.executor = DuckDbExecutor()

    def _rows(self, relation: object) -> list[tuple[object, ...]]:
        source = self.service.relations.reference(relation)
        return list(self.service.relations.query(
            f"SELECT * FROM {source} ORDER BY 1",
        ).fetchall())

    def test_kinds_are_the_exact_duckdb_instruction_set(self) -> None:
        self.assertEqual(
            DuckDbExecutor.kinds,
            (
                InstructionKind("source_relation", "duckdb"),
                InstructionKind("sql", "duckdb"),
                InstructionKind("aggregate", "duckdb"),
                InstructionKind("deduplication", "duckdb"),
                InstructionKind("merging", "duckdb"),
                InstructionKind("conflict_findings", "duckdb"),
            ),
        )

    def test_sql_materializes_a_relation(self) -> None:
        step = _step(
            "sql",
            Instruction(
                InstructionKind("sql", "duckdb"),
                {"relation": "answer", "sql": "SELECT 42 AS value"},
            ),
        )

        outcome = self.executor.execute(
            _context(step, self.resources),
            step.instruction,
        )

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(len(outcome.artifacts), 1)
        self.assertEqual(self._rows(outcome.artifacts[0].value), [(42,)])

    def test_deduplication_returns_distinct_rows(self) -> None:
        source = self.service.relations.materialize(
            "duplicate_source",
            "SELECT * FROM (VALUES (1), (1), (2)) AS rows(value)",
        )
        step = _step(
            "deduplication",
            Instruction(
                InstructionKind("deduplication", "duckdb"),
                {"relation": "distinct_records"},
            ),
        )

        outcome = self.executor.execute(
            _context(
                step,
                self.resources,
                {"records": (_artifact("value", source),)},
            ),
            step.instruction,
        )

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(self._rows(outcome.artifacts[0].value), [(1,), (2,)])

    def test_aggregate_unions_every_input_relation(self) -> None:
        first = self.service.relations.materialize(
            "first_source",
            "SELECT * FROM (VALUES (1), (2)) AS rows(value)",
        )
        second = self.service.relations.materialize(
            "second_source",
            "SELECT * FROM (VALUES (3)) AS rows(value)",
        )
        step = _step(
            "aggregate",
            Instruction(
                InstructionKind("aggregate", "duckdb"),
                {"relation": "all_records"},
            ),
        )

        outcome = self.executor.execute(
            _context(
                step,
                self.resources,
                {
                    "first": (_artifact("first", first),),
                    "second": (_artifact("second", second),),
                },
            ),
            step.instruction,
        )

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(
            self._rows(outcome.artifacts[0].value), [(1,), (2,), (3,)],
        )

    def test_a_disrupted_context_is_skipped(self) -> None:
        step = _step(
            "sql",
            Instruction(
                InstructionKind("sql", "duckdb"),
                {"relation": "unused", "sql": "SELECT 1"},
            ),
        )
        context = DisruptedExecutionContext(
            step=step,
            runtime_configuration={},
            inputs={},
            disruptions=(),
            resources=self.resources,
            logger=None,
        )

        outcome = self.executor.execute(context, step.instruction)

        self.assertEqual(outcome.status, StepStatus.SKIPPED)

    def test_an_unknown_kind_raises(self) -> None:
        step = _step(
            "unknown",
            Instruction(
                InstructionKind("unknown", "duckdb"), {"relation": "unused"},
            ),
        )

        with self.assertRaisesRegex(ValueError, "unknown instruction kind"):
            self.executor.execute(_context(step, self.resources), step.instruction)
