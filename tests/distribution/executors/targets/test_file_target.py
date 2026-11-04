from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from kg_build_system.distribution.modules.runtime import RuntimeResources
from kg_build_system.distribution.modules.duckdb import (
    DuckDbExecutor,
    DuckDbResourceProvider,
)
from kg_build_system.distribution.modules.file import (
    FileConfiguration,
    FileExecutor,
    FilePlanner,
)
from kg_build_system.kernel import (
    ArtifactType,
    Input,
    Instruction,
    Output,
    PlanContext,
    Step,
    Toolchain,
    WorkflowPlan,
)
from kg_build_system.kernel.service._private.runtime import WorkflowRuntime

from ._support import component, connection, record_type


class _FakeLinker:
    requires: tuple[str, ...] = ()

    def link(self, layers: Any) -> object:
        return object()


class FileTargetTests(unittest.TestCase):
    def test_a_file_plan_writes_the_received_graph_records(self) -> None:
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
        planner = FilePlanner(FileConfiguration("graph.jsonl"))
        (file_step,) = planner.plan(object(), PlanContext())
        plan = WorkflowPlan(
            components=(
                component("core", "4"),
                component(
                    planner.component_id, planner.version, planner.runtime_fields,
                ),
            ),
            steps=(source, file_step),
            connections=(
                connection(
                    ("file", "write", "records"),
                    ("core", "records", "records"),
                ),
            ),
        )
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            executors=(DuckDbExecutor(), FileExecutor()),
            runtime=WorkflowRuntime(
                providers=(RuntimeResources(), DuckDbResourceProvider()),
            ),
        )

        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = toolchain.execute(plan, output_directory=root)
            self.assertTrue(
                report.succeeded,
                [failure.message for failure in report.unresolved_failures],
            )
            path = root / "graph.jsonl"
            self.assertTrue(path.is_file())
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(
            records,
            [
                {
                    "build_key": "person-1",
                    "kind": "node",
                    "name": "Alice",
                    "type": "Person",
                },
                {
                    "build_key": "person-2",
                    "kind": "node",
                    "name": "Bob",
                    "type": "Person",
                },
            ],
        )

    def test_the_runtime_path_replaces_the_compiled_path(self) -> None:
        planner = FilePlanner(FileConfiguration("compiled.jsonl"))
        (file_step,) = planner.plan(object(), PlanContext())
        self.assertEqual(
            file_step.inputs,
            (Input(ArtifactType("core", "graph.*"), None, "records"),),
        )
        self.assertEqual(
            file_step.instruction.payload, {"relative_path": "compiled.jsonl"},
        )


if __name__ == "__main__":
    unittest.main()
