from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system.distribution.executors.duckdb import (
    DuckDbExecutor,
    DuckDbResourceProvider,
    RelationRef,
)
from kg_build_system.kernel import (
    ArtifactType,
    Component,
    Instruction,
    Publication,
    Step,
    Toolchain,
    WorkflowPlan,
    WorkflowReport,
)
from kg_build_system.kernel.service._private.runtime import WorkflowRuntime

VALUE = ArtifactType("core", "value")


class _FakeLinker:
    requires: tuple[str, ...] = ()

    def link(self, layers):
        return object()


class ToolchainExecutionTests(unittest.TestCase):
    def test_a_sql_step_publishes_its_relation(self) -> None:
        step = Step(
            "core",
            "sql",
            (),
            (Publication(VALUE, "value"),),
            Instruction(
                ("sql", "duckdb"),
                {"relation": "published", "sql": "SELECT 42 AS value"},
            ),
        )
        plan = WorkflowPlan(
            components=(Component("core", "1"),),
            steps=(step,),
        )
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            executors=(DuckDbExecutor(),),
            resources=DuckDbResourceProvider(),
            runtime=WorkflowRuntime(),
        )

        with TemporaryDirectory() as directory:
            report = toolchain.execute(
                plan, output_directory=Path(directory),
            )

        self.assertIsInstance(report, WorkflowReport)
        self.assertTrue(report.succeeded)
        self.assertEqual(len(report.published_artifacts), 1)
        published = report.published_artifacts[0]
        self.assertEqual(published.type, VALUE)
        self.assertIsInstance(published.value, RelationRef)
        assert isinstance(published.value, RelationRef)
        self.assertEqual(published.value.name, "published")


if __name__ == "__main__":
    unittest.main()
