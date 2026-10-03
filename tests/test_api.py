from __future__ import annotations

import unittest
from pathlib import Path

from kg_build_system import compile, create_blueprint
from kg_build_system.modules import (
    FileModule,
    FileModuleConfiguration,
    register_module,
)

from reference_project.build import compile_reference_build, create_reference_blueprint


class CompositionApiTests(unittest.TestCase):
    def test_modules_only_uses_the_calling_file_namespace(self) -> None:
        blueprint = create_reference_blueprint()
        contract = compile_reference_build()

        self.assertTrue(blueprint.bindings)
        self.assertTrue(blueprint.sources)
        self.assertEqual(blueprint.modules[-1].module_id, "core")
        self.assertEqual(
            tuple(
                contribution.reference.module_id
                for contribution in contract.workflow.contributions
            ),
            tuple(module.module_id for module in blueprint.modules),
        )
        self.assertTrue(contract.workflow.connections)

    def test_explicit_namespace_path_is_supported(self) -> None:
        blueprint = create_blueprint(
            namespace_path=Path(__file__).parents[1] / "reference_project",
            modules=(),
        )

        self.assertTrue(blueprint.bindings)
        self.assertTrue(blueprint.sources)

    def test_blueprint_compilation_replaces_its_module_composition(self) -> None:
        # The blueprint names five modules; one is enough to read what core
        # writes, so that one and the mandatory core are all the contract holds.
        blueprint = create_reference_blueprint()
        contract = compile(
            blueprint=blueprint,
            modules=(register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),),
        )

        self.assertEqual(
            tuple(
                contribution.reference.module_id
                for contribution in contract.workflow.contributions
            ),
            ("file", "core"),
        )


if __name__ == "__main__":
    unittest.main()
