from __future__ import annotations

import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from kg_build_system.api import default_toolchain
from kg_build_system.distribution import (
    DuckDbSourcePlanner,
    FileConfiguration,
    FilePlanner,
    create_blueprint,
)
from kg_build_system.distribution.modules.core import RowSourcePlanner, core_planners
from kg_build_system.kernel import (
    InstructionKind, PlanContext, Step, Toolchain,
)


def _named(steps: tuple[Step, ...], prefix: str) -> Iterator[Step]:
    return (step for step in steps if step.name.startswith(prefix))


class _FakeLinker:
    def link(self, languages: Any, namespace: Any) -> object:
        return object()


class CorePlannersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        cls.planners = core_planners()
        cls.source_planner = DuckDbSourcePlanner()
        context = PlanContext()
        cls.steps = (
            *tuple(cls.source_planner.plan(cls.blueprint, context)),
            *(
                step
                for planner in cls.planners
                for step in planner.plan(cls.blueprint, context)
            ),
        )

    def test_core_planners_share_the_core_component(self) -> None:
        self.assertEqual(len(self.planners), 4)
        for planner in self.planners:
            with self.subTest(planner=type(planner).__name__):
                self.assertEqual(planner.component_id, "core")
                self.assertEqual(planner.version, "4")
                self.assertEqual(planner.runtime_fields, ())

    def test_the_source_planner_owns_the_duckdb_component(self) -> None:
        self.assertEqual(self.source_planner.component_id, "duckdb")
        self.assertEqual(self.source_planner.version, "1")
        self.assertEqual(self.source_planner.runtime_fields, ())

    def test_a_caller_supplied_core_planner_replaces_the_default_group(self) -> None:
        supplied = RowSourcePlanner()

        toolchain = default_toolchain(planners=(supplied,))

        self.assertEqual(
            [type(planner) for planner in toolchain.planners],
            [DuckDbSourcePlanner, RowSourcePlanner],
        )
        self.assertIs(toolchain.planners[1], supplied)

    def test_the_core_planner_emits_every_step_shape(self) -> None:
        for prefix in (
            "source.", "projection.", "binding.", "aggregate.",
        ):
            with self.subTest(prefix=prefix):
                self.assertTrue(any(_named(self.steps, prefix)))

    def test_the_assembled_core_plan_keeps_the_step_order(self) -> None:
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            planners=(
                DuckDbSourcePlanner(),
                *core_planners(),
                FilePlanner(FileConfiguration("graph.jsonl")),
            ),
        )

        plan = toolchain.compile(self.blueprint)

        self.assertEqual(
            [component.id for component in plan.components].count("duckdb"),
            1,
        )
        self.assertEqual(
            [component.id for component in plan.components].count("core"),
            1,
        )
        planned_steps = tuple(
            step for step in plan.steps
            if step.component in {"duckdb", "core"}
        )
        self.assertEqual(
            [step.name for step in planned_steps],
            [step.name for step in self.steps],
        )

    def test_source_steps_use_the_source_relation_instruction(self) -> None:
        sources = tuple(_named(self.steps, "source."))
        self.assertTrue(sources)
        for step in sources:
            self.assertEqual(
                step.instruction.kind,
                InstructionKind("source_relation", "duckdb"),
            )
            payload = step.instruction.payload
            assert isinstance(payload, dict)
            self.assertEqual(
                set(payload),
                {
                    "relation", "location", "format", "credential_reference",
                    "declaration", "declared_columns", "declared_paths",
                },
            )

    def test_source_steps_are_sorted_by_relation_name(self) -> None:
        sources = tuple(_named(self.steps, "source."))
        self.assertEqual(
            [step.name for step in sources], sorted(step.name for step in sources),
        )

    def test_projection_and_binding_steps_use_sql(self) -> None:
        relational = (
            *tuple(_named(self.steps, "projection.")),
            *tuple(_named(self.steps, "binding.")),
        )
        self.assertTrue(relational)
        for step in relational:
            self.assertEqual(step.instruction.kind, InstructionKind("sql", "duckdb"))
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
            self.assertEqual(
                step.instruction.kind, InstructionKind("aggregate", "duckdb"),
            )
            self.assertEqual(step.assembly_preference, "deferred")


if __name__ == "__main__":
    unittest.main()
