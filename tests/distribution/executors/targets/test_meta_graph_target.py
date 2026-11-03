from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from kg_build_system.distribution.executors.duckdb import (
    DuckDbExecutor,
    DuckDbResourceProvider,
)
from kg_build_system.distribution.executors.meta_graph import (
    MetaGraphConfiguration,
    MetaGraphExecutor,
    MetaGraphPlanner,
)
from kg_build_system.kernel import (
    Instruction,
    Output,
    PlanContext,
    Step,
    Toolchain,
    WorkflowPlan,
)
from kg_build_system.kernel.service._private.runtime import WorkflowRuntime

from ._support import bound_blueprint, component, connection, node, record_type


class _FakeLinker:
    requires: tuple[str, ...] = ()

    def link(self, layers: Any) -> object:
        return object()


def _plan(configuration: MetaGraphConfiguration) -> WorkflowPlan:
    source = Step(
        "core",
        "records",
        (),
        (Output(record_type("Person"), "records"),),
        Instruction(
            ("sql", "duckdb"),
            {
                "relation": "person_records",
                "sql": (
                    "SELECT * FROM (VALUES "
                    "('person-1', 'Alice'), ('person-2', 'Bob')"
                    ") AS rows(build_key, name)"
                ),
            },
        ),
    )
    planner = MetaGraphPlanner(configuration)
    model = bound_blueprint(node("Person", "name"))
    (document_step,) = planner.plan(model, PlanContext())
    return WorkflowPlan(
        components=(
            component("core", "4"),
            component(
                planner.component_id, planner.version, planner.runtime_fields,
            ),
        ),
        steps=(source, document_step),
        connections=(
            connection(
                ("meta_graph", "document", "records"),
                ("core", "records", "records"),
            ),
        ),
    )


class MetaGraphTargetTests(unittest.TestCase):
    def test_the_meta_graph_document_contains_the_component_summary(self) -> None:
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            executors=(DuckDbExecutor(), MetaGraphExecutor()),
            resources=DuckDbResourceProvider(),
            runtime=WorkflowRuntime(),
        )
        plan = _plan(MetaGraphConfiguration())

        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = toolchain.execute(plan, output_directory=root)
            self.assertTrue(
                report.succeeded,
                [failure.message for failure in report.unresolved_failures],
            )
            document = json.loads(
                (root / "meta_graph.json").read_text(encoding="utf-8")
            )
            self.assertTrue((root / "meta_graph.html").is_file())

        self.assertEqual(document["summary"]["node_components"], 1)
        self.assertEqual(document["summary"]["total_nodes"], 2)
        self.assertEqual(document["nodes"][0]["name"], "Person")
        self.assertEqual(document["nodes"][0]["counts"]["records"], 2)
        self.assertEqual(
            document["nodes"][0]["properties"][0]["examples"], ["Alice", "Bob"],
        )

    def test_disabling_html_writes_no_page(self) -> None:
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            executors=(DuckDbExecutor(), MetaGraphExecutor()),
            resources=DuckDbResourceProvider(),
            runtime=WorkflowRuntime(),
        )
        plan = _plan(MetaGraphConfiguration(include_html=False))

        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = toolchain.execute(plan, output_directory=root)
            self.assertTrue(report.succeeded)
            self.assertTrue((root / "meta_graph.json").is_file())
            self.assertFalse((root / "meta_graph.html").exists())


if __name__ == "__main__":
    unittest.main()
