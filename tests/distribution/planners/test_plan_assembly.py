from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from kg_build_system.distribution.executors.file import (
    FileConfiguration,
    FilePlanner,
)
from kg_build_system.distribution.interpreter import create_blueprint
from kg_build_system.distribution.planners import (
    CorePlanner,
    DeduplicationPlanner,
)
from kg_build_system.kernel import StepOutcome, StepStatus, Toolchain


class FakeLinker:
    requires: tuple[str, ...] = ()

    def link(self, layers: Any) -> object:
        return object()


class FakeExecutor:
    kinds = (
        ("source_relation", "duckdb"),
        ("sql", "duckdb"),
        ("aggregate", "duckdb"),
        ("deduplication", "duckdb"),
        ("file", "default"),
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
            planners=(CorePlanner(), DeduplicationPlanner()),
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
                CorePlanner(),
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
            ["core", "deduplication", "file"],
        )
        identities = {f"{step.component}.{step.name}" for step in plan.steps}
        for connection in plan.connections:
            self.assertTrue(any(
                connection.input_id.startswith(f"{identity}.")
                for identity in identities
            ))
            self.assertTrue(any(
                connection.output_id.startswith(f"{identity}.")
                for identity in identities
            ))
        self.assertTrue(any(
            connection.output_id.startswith("deduplication.")
            for connection in plan.connections
        ))


if __name__ == "__main__":
    unittest.main()
