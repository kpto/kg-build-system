from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system.distribution.executors.duckdb import (
    DuckDbExecutor,
    DuckDbResourceProvider,
)
from kg_build_system.distribution.executors.runtime import ExecutionServices
from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    ContinuableInput,
    DisruptedExecutionContext,
    ExecutionContext,
    Input,
    Instruction,
    Output,
    RuntimeConfiguration,
    Step,
    StepStatus,
    WorkflowPlan,
)

RECORDS = ArtifactType("core", "records")
RESULT = ArtifactType("core", "result")


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
        (Output(output_type, "value"),),
        instruction,
    )


def _context(
    step: Step,
    services: ExecutionServices,
    inputs: dict[str, tuple[ContinuableInput, ...]] | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        step=step,
        step_id=f"core.{step.name}",
        component="core",
        runtime_configuration={},
        inputs=inputs or {},
        services=services,
    )


def _artifact(name: str, value: object) -> ContinuableInput:
    return ContinuableInput(
        f"core.source.{name}",
        StepStatus.SUCCEEDED,
        Artifact(name, RECORDS, value),
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
        self.services = self.provider.services(WorkflowPlan((), ()), configuration)
        self.addCleanup(lambda: self.provider.close(self.services))
        self.executor = DuckDbExecutor()

    def _rows(self, relation: object) -> list[tuple[object, ...]]:
        source = self.services.relations.reference(relation)
        return list(self.services.relations.query(
            f"SELECT * FROM {source} ORDER BY 1",
        ).fetchall())

    def test_kinds_are_the_exact_duckdb_instruction_set(self) -> None:
        self.assertEqual(
            DuckDbExecutor.kinds,
            (
                ("source_relation", "duckdb"),
                ("sql", "duckdb"),
                ("aggregate", "duckdb"),
                ("deduplication", "duckdb"),
                ("merging", "duckdb"),
                ("conflict_findings", "duckdb"),
            ),
        )

    def test_sql_materializes_a_relation(self) -> None:
        step = _step(
            "sql",
            Instruction(
                ("sql", "duckdb"),
                {"relation": "answer", "sql": "SELECT 42 AS value"},
            ),
        )

        outcome = self.executor.execute(
            _context(step, self.services),
            step.instruction,
        )

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(len(outcome.artifacts), 1)
        self.assertEqual(self._rows(outcome.artifacts[0].value), [(42,)])

    def test_deduplication_returns_distinct_rows(self) -> None:
        source = self.services.relations.materialize(
            "duplicate_source",
            "SELECT * FROM (VALUES (1), (1), (2)) AS rows(value)",
        )
        step = _step(
            "deduplication",
            Instruction(
                ("deduplication", "duckdb"), {"relation": "distinct_records"},
            ),
        )

        outcome = self.executor.execute(
            _context(
                step,
                self.services,
                {"records": (_artifact("value", source),)},
            ),
            step.instruction,
        )

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(self._rows(outcome.artifacts[0].value), [(1,), (2,)])

    def test_aggregate_unions_every_input_relation(self) -> None:
        first = self.services.relations.materialize(
            "first_source",
            "SELECT * FROM (VALUES (1), (2)) AS rows(value)",
        )
        second = self.services.relations.materialize(
            "second_source",
            "SELECT * FROM (VALUES (3)) AS rows(value)",
        )
        step = _step(
            "aggregate",
            Instruction(("aggregate", "duckdb"), {"relation": "all_records"}),
        )

        outcome = self.executor.execute(
            _context(
                step,
                self.services,
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
            Instruction(("sql", "duckdb"), {"relation": "unused", "sql": "SELECT 1"}),
        )
        context = DisruptedExecutionContext(
            step=step,
            step_id="core.sql",
            component="core",
            runtime_configuration={},
            inputs={},
            disruptions=(),
            services=self.services,
        )

        outcome = self.executor.execute(context, step.instruction)

        self.assertEqual(outcome.status, StepStatus.SKIPPED)

    def test_an_unknown_kind_raises(self) -> None:
        step = _step(
            "unknown",
            Instruction(("unknown", "duckdb"), {"relation": "unused"}),
        )

        with self.assertRaisesRegex(ValueError, "unknown instruction kind"):
            self.executor.execute(_context(step, self.services), step.instruction)
