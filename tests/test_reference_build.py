from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kg_build_system.declaration.blueprint import GraphBlueprint
from kg_build_system.pipeline.build import build
from kg_build_system.pipeline.contract import WorkflowContractDTO
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
        self.assertTrue(blueprint.sources)

    def test_the_reference_project_compiles_and_builds(self) -> None:
        contract = compile_reference_build()
        self.assertIsInstance(contract, WorkflowContractDTO)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = build(contract, output_directory=root)
            self.assertTrue(
                report.succeeded,
                [failure.message for failure in report.unresolved_failures],
            )
            names = {artifact.type.name for artifact in report.published_artifacts}
            self.assertIn("write_result", names)
            self.assertIn("meta_graph_document", names)
            self.assertIn("import_bundle", names)
            self.assertTrue((root / "graph.jsonl").is_file())
            self.assertTrue((root / "meta_graph.json").is_file())
            self.assertTrue((root / "neo4j-import").is_dir())


if __name__ == "__main__":
    unittest.main()
