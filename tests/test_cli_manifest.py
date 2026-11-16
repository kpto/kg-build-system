from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from kg_build_system import Blueprint, Workflow, default_toolchain
from kg_build_system.cli import main
from kg_build_system.cli.service._private.manifest_command import read_manifest
from kg_build_system.distribution.interpreter.service._private.discovery import (
    namespace_modules,
)

REFERENCE = Path(__file__).parent.parent / "reference_project"


def _write_manifest(directory: Path, body: str) -> None:
    (directory / "__init__.py").write_text("")
    (directory / "manifest.py").write_text(body)


class ManifestValueTests(unittest.TestCase):
    def test_a_blueprint_states_exactly_one_source(self) -> None:
        with self.assertRaises(ValueError):
            Blueprint()
        with self.assertRaises(ValueError):
            Blueprint(namespace_path=".", bindings=(object(),))

    def test_a_workflow_states_planners_or_a_toolchain(self) -> None:
        blueprint = Blueprint(namespace_path=".")
        with self.assertRaises(ValueError):
            Workflow(
                blueprint=blueprint,
                planners=(object(),),
                toolchain=default_toolchain(),
            )

    def test_the_manifest_values_are_found_by_type_not_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            _write_manifest(
                root,
                "from pathlib import Path\n"
                "from kg_build_system import Blueprint, Workflow\n"
                "composition = Blueprint(namespace_path=Path(__file__).parent)\n"
                "build = Workflow(blueprint=composition)\n",
            )
            blueprint, workflow = read_manifest(root)

        self.assertIsInstance(blueprint, Blueprint)
        self.assertIsInstance(workflow, Workflow)

    def test_two_blueprints_are_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            _write_manifest(
                root,
                "from pathlib import Path\n"
                "from kg_build_system import Blueprint\n"
                "first = Blueprint(namespace_path=Path(__file__).parent)\n"
                "second = Blueprint(namespace_path=Path(__file__).parent)\n",
            )
            with self.assertRaises(ValueError):
                read_manifest(root)

    def test_a_workflow_supplies_its_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            _write_manifest(
                root,
                "from pathlib import Path\n"
                "from kg_build_system import Blueprint, Workflow\n"
                "build = Workflow(\n"
                "    blueprint=Blueprint(namespace_path=Path(__file__).parent)\n"
                ")\n",
            )
            blueprint, workflow = read_manifest(root)

        self.assertIsNotNone(workflow)
        self.assertIs(blueprint, workflow.blueprint)

    def test_discovery_skips_the_manifest(self) -> None:
        names = {module.__name__ for module in namespace_modules(REFERENCE)}

        self.assertIn("reference_project", names)
        self.assertNotIn("reference_project.manifest", names)


class ManifestCommandTests(unittest.TestCase):
    def test_the_blueprint_command_writes_the_blueprint_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "blueprint.json"
            self.assertEqual(
                main([
                    "blueprint", "--project", str(REFERENCE),
                    "--output", str(output),
                ]),
                0,
            )
            document = json.loads(output.read_text())

        self.assertTrue(document["graph"]["nodes"])
        self.assertTrue(document["bindings"])

    def test_the_workflow_command_writes_the_plan_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.json"
            self.assertEqual(
                main([
                    "workflow", "--project", str(REFERENCE),
                    "--output", str(output),
                ]),
                0,
            )
            document = json.loads(output.read_text())

        self.assertTrue(document["steps"])
        self.assertTrue(document["provenance"]["blueprint"]["graph"]["nodes"])

    def test_the_blueprint_command_does_not_compile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            _write_manifest(
                root,
                "from pathlib import Path\n"
                "from kg_build_system import Blueprint, Workflow\n"
                "composition = Blueprint(namespace_path=Path(__file__).parent)\n"
                "build = Workflow(blueprint=composition, planners=(object(),))\n",
            )
            output = Path(directory) / "blueprint.json"
            self.assertEqual(
                main([
                    "blueprint", "--project", str(root),
                    "--output", str(output),
                ]),
                0,
            )
            self.assertTrue(output.is_file())

            with self.assertRaises(Exception):
                main([
                    "workflow", "--project", str(root),
                    "--output", str(Path(directory) / "plan.json"),
                ])

    def test_the_run_command_executes_the_reference_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory) / "build"
            stream = io.StringIO()
            with redirect_stdout(stream):
                status = main([
                    "run", "--project", str(REFERENCE),
                    "--output-directory", str(output_directory),
                ])
            report = json.loads(stream.getvalue())
            records = [
                json.loads(line)
                for line in (output_directory / "graph.jsonl").read_text().splitlines()
            ]

        self.assertEqual(status, 0)
        self.assertTrue(report["published_artifacts"])
        self.assertEqual(len([row for row in records if row["kind"] == "node"]), 21)
        self.assertEqual(len([row for row in records if row["kind"] == "edge"]), 21)


if __name__ == "__main__":
    unittest.main()
