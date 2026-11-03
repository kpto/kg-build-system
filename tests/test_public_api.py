from __future__ import annotations

import inspect
import unittest

import kg_build_system
from kg_build_system import create_blueprint
from kg_build_system.declaration.blueprint import GraphBlueprint
from kg_build_system.pipeline.build import build
from kg_build_system.pipeline.compilation import compile_blueprint
from kg_build_system.pipeline.contract import WorkflowContractDTO


class PublicApiTests(unittest.TestCase):
    def test_every_export_resolves(self) -> None:
        for name in kg_build_system.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(kg_build_system, name))

    def test_compile_is_the_function_not_the_package(self) -> None:
        self.assertTrue(callable(kg_build_system.compile))
        self.assertFalse(inspect.ismodule(kg_build_system.compile))
        self.assertEqual(kg_build_system.compile.__module__, "kg_build_system.api")

    def test_the_canonical_entry_points_are_distinct(self) -> None:
        self.assertTrue(callable(kg_build_system.create_blueprint))
        self.assertTrue(callable(kg_build_system.compile))
        self.assertTrue(callable(kg_build_system.build))
        self.assertIsNot(kg_build_system.compile, compile_blueprint)

    def test_the_public_handles_name_their_artifacts(self) -> None:
        self.assertEqual(
            GraphBlueprint.__module__,
            "kg_build_system.declaration.blueprint.public.dto.graph_blueprint",
        )
        self.assertEqual(
            WorkflowContractDTO.__module__,
            "kg_build_system.pipeline.contract.public.dto.contract",
        )
        self.assertEqual(create_blueprint.__module__, "kg_build_system.api")
        self.assertEqual(compile_blueprint.__module__, "kg_build_system.pipeline.compilation.public.service.compile")
        self.assertEqual(build.__module__, "kg_build_system.pipeline.build.public.service.build")


if __name__ == "__main__":
    unittest.main()
