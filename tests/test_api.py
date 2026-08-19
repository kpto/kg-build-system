from __future__ import annotations

import unittest
from pathlib import Path

from kg_build_system import compile, create_blueprint

from demo.build import compile_demo, create_demo_blueprint


class CompositionApiTests(unittest.TestCase):
    def test_modules_only_uses_the_calling_file_namespace(self) -> None:
        blueprint = create_demo_blueprint()
        contract = compile_demo()

        self.assertTrue(blueprint.bindings)
        self.assertTrue(blueprint.sources)
        self.assertEqual(blueprint.modules[-1].module_id, "core")
        self.assertTrue(contract.workflow.steps)

    def test_explicit_namespace_path_is_supported(self) -> None:
        blueprint = create_blueprint(
            namespace_path=Path(__file__).parents[1] / "demo",
            modules=(),
        )

        self.assertTrue(blueprint.bindings)
        self.assertTrue(blueprint.sources)

    def test_blueprint_compilation_replaces_its_module_composition(self) -> None:
        blueprint = create_demo_blueprint()
        contract = compile(blueprint=blueprint, modules=())

        self.assertEqual(
            tuple(
                module.reference.module_id
                for module in contract.workflow.modules
            ),
            ("core",),
        )


if __name__ == "__main__":
    unittest.main()
