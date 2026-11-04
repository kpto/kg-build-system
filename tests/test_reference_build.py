from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kg_build_system import execute
from kg_build_system.distribution.interpreter import GraphBlueprint
from kg_build_system.kernel import WorkflowPlan
from reference_project.build import (
    compile_reference_build,
    create_reference_blueprint,
)


class ReferenceBuildTests(unittest.TestCase):
    def test_the_reference_blueprint_is_a_graph_blueprint(self) -> None:
        blueprint = create_reference_blueprint()

        self.assertIsInstance(blueprint, GraphBlueprint)
        self.assertTrue(blueprint.graph.nodes)
        self.assertTrue(blueprint.bindings)
        self.assertTrue(blueprint.assets.assets)

    def test_the_reference_project_compiles_and_builds(self) -> None:
        plan = compile_reference_build()
        self.assertIsInstance(plan, WorkflowPlan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = execute(plan, output_directory=root)
            self.assertTrue(
                report.succeeded,
                [failure.message for failure in report.unresolved_failures],
            )
            names = {artifact.type.name for artifact in report.published_artifacts}
            self.assertIn("write_result", names)
            self.assertIn("meta_graph_document", names)
            self.assertIn("import_bundle", names)
            self.assertFalse(
                [
                    artifact
                    for artifact in report.published_artifacts
                    if artifact.type.namespace == "core"
                ],
                "intermediate graph records must not be published",
            )
            self.assertTrue((root / "graph.jsonl").is_file())
            self.assertTrue((root / "meta_graph.json").is_file())
            self.assertTrue((root / "meta_graph.html").is_file())
            self.assertTrue((root / "neo4j-import").is_dir())
            self.assertTrue(
                (root / "neo4j-import" / "import_neo4j.py").is_file(),
            )
            self.assertTrue((root / "workflow_plan.json").is_file())
            self.assertTrue((root / "build_report.json").is_file())


if __name__ == "__main__":
    unittest.main()
