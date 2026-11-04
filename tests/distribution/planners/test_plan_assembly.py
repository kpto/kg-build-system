from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from kg_build_system.distribution import (
    DeduplicationPlanner,
    DuckDbSourcePlanner,
    FileConfiguration,
    FilePlanner,
)
from kg_build_system.distribution.interpreter import create_blueprint
from kg_build_system.distribution.modules.core import core_planners
from kg_build_system.kernel import (
    InstructionKind, StepOutcome, StepStatus, Toolchain, step_id,
)


class FakeLinker:
    requires: tuple[str, ...] = ()

    def link(self, layers: Any) -> object:
        return object()


class FakeExecutor:
    kinds = (
        InstructionKind("source_relation", "duckdb"),
        InstructionKind("sql", "duckdb"),
        InstructionKind("aggregate", "duckdb"),
        InstructionKind("deduplication", "duckdb"),
        InstructionKind("file", "default"),
    )

    def execute(self, context: Any, instruction: Any) -> StepOutcome:
        return StepOutcome(context.step_id, StepStatus.SUCCEEDED)


class PlanAssemblyTests(unittest.TestCase):
    def test_an_unread_deduplication_output_is_refused(self) -> None:
        blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=FakeLinker(),
            planners=(
                DuckDbSourcePlanner(), *core_planners(), DeduplicationPlanner(),
            ),
            executors=(FakeExecutor(),),
        )

        with self.assertRaisesRegex(ValueError, "nothing reads"):
            toolchain.compile(blueprint)

    def test_a_consumer_lets_core_and_deduplication_assemble(self) -> None:
        blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=FakeLinker(),
            planners=(
                DuckDbSourcePlanner(),
                *core_planners(),
                DeduplicationPlanner(),
                FilePlanner(FileConfiguration("graph.jsonl")),
            ),
            executors=(FakeExecutor(),),
        )

        plan = toolchain.compile(blueprint)

        self.assertTrue(plan.connections)
        self.assertTrue(plan.steps)
        self.assertTrue(all(step.component for step in plan.steps))
        self.assertEqual(
            [component.id for component in plan.components],
            ["duckdb", "core", "deduplication", "file"],
        )
        identities = {step_id(step) for step in plan.steps}
        for connection in plan.connections:
            self.assertIn(connection.input.step, identities)
            self.assertIn(connection.output.step, identities)
        self.assertTrue(any(
            connection.output.step.component == "deduplication"
            for connection in plan.connections
        ))


if __name__ == "__main__":
    unittest.main()
