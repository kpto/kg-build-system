from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from kg_build_system.distribution.executors.duckdb import (
    DuckDbExecutor,
    DuckDbResourceProvider,
)
from kg_build_system.distribution.executors.neo4j import (
    Neo4jConfiguration,
    Neo4jExecutor,
    Neo4jPlanner,
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


def _plan(configuration: Neo4jConfiguration) -> WorkflowPlan:
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
    planner = Neo4jPlanner(configuration)
    model = bound_blueprint(node("Person", "name"))
    export, script = planner.plan(model, PlanContext())
    return WorkflowPlan(
        components=(
            component("core", "4"),
            component(
                planner.component_id, planner.version, planner.runtime_fields,
            ),
        ),
        steps=(source, export, script),
        connections=(
            connection(
                ("neo4j", export.name, "records"),
                ("core", "records", "records"),
            ),
            connection(
                ("neo4j", "script", "components"),
                ("neo4j", export.name, "result"),
            ),
        ),
    )


class Neo4jTargetTests(unittest.TestCase):
    def test_the_import_bundle_contains_profiles_and_an_executable_script(self) -> None:
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            executors=(DuckDbExecutor(), Neo4jExecutor()),
            resources=DuckDbResourceProvider(),
            runtime=WorkflowRuntime(),
        )
        plan = _plan(Neo4jConfiguration())

        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = toolchain.execute(plan, output_directory=root)
            self.assertTrue(
                report.succeeded,
                [failure.message for failure in report.unresolved_failures],
            )
            bundle = root / "neo4j-import"
            self.assertTrue(bundle.is_dir())
            node_files = list((bundle / "nodes").glob("*.parquet"))
            self.assertEqual(len(node_files), 1)
            script = bundle / "import_neo4j.py"
            self.assertTrue(script.is_file())
            if os.name != "nt":
                self.assertTrue(script.stat().st_mode & 0o111)
            summary = {
                artifact.type.name: artifact.value
                for artifact in report.published_artifacts
            }
            self.assertEqual(summary["import_bundle"]["nodes"], 2)
            self.assertEqual(
                summary["import_bundle"]["node_files"],
                ["nodes/" + node_files[0].name],
            )


if __name__ == "__main__":
    unittest.main()
