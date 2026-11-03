from __future__ import annotations

import unittest
from collections.abc import Iterator
from pathlib import Path

from kg_build_system.distribution.interpreter import create_blueprint
from kg_build_system.distribution.planners import CorePlanner
from kg_build_system.kernel import PlanContext, Step


def _named(steps: tuple[Step, ...], prefix: str) -> Iterator[Step]:
    return (step for step in steps if step.name.startswith(prefix))


class CorePlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        cls.steps = tuple(CorePlanner().plan(cls.blueprint, PlanContext()))

    def test_the_core_planner_emits_every_step_shape(self) -> None:
        for prefix in ("table.", "projection.", "binding.", "aggregate."):
            with self.subTest(prefix=prefix):
                self.assertTrue(any(_named(self.steps, prefix)))

    def test_source_steps_use_the_source_relation_instruction(self) -> None:
        sources = tuple(_named(self.steps, "table."))
        self.assertTrue(sources)
        for step in sources:
            self.assertEqual(step.instruction.kind, ("source_relation", "duckdb"))
            payload = step.instruction.payload
            assert isinstance(payload, dict)
            self.assertEqual(
                set(payload),
                {
                    "relation", "location", "format", "credential_reference",
                    "declaration", "declared_columns", "declared_paths",
                },
            )

    def test_projection_and_binding_steps_use_sql(self) -> None:
        relational = (
            *tuple(_named(self.steps, "projection.")),
            *tuple(_named(self.steps, "binding.")),
        )
        self.assertTrue(relational)
        for step in relational:
            self.assertEqual(step.instruction.kind, ("sql", "duckdb"))
            payload = step.instruction.payload
            assert isinstance(payload, dict)
            self.assertIn("relation", payload)
            self.assertIn("sql", payload)

    def test_binding_sql_names_its_graph_symbol(self) -> None:
        bindings = tuple(_named(self.steps, "binding."))
        self.assertTrue(bindings)
        for step in bindings:
            payload = step.instruction.payload
            assert isinstance(payload, dict)
            self.assertIn("_kg_binding_symbol", payload["sql"])

    def test_aggregate_steps_are_deferred(self) -> None:
        aggregates = tuple(_named(self.steps, "aggregate."))
        self.assertTrue(aggregates)
        for step in aggregates:
            self.assertEqual(step.instruction.kind, ("aggregate", "duckdb"))
            self.assertEqual(step.assembly_preference, "deferred")


if __name__ == "__main__":
    unittest.main()
