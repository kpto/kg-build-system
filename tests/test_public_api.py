from __future__ import annotations

import importlib
import inspect
import unittest

import kg_build_system
from kg_build_system import create_blueprint
from kg_build_system.declaration.blueprint import GraphBlueprint
from kg_build_system.pipeline.build import BuildRuntime, WorkflowReport, build
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

    def test_the_type_vocabulary_is_exported_at_the_root(self) -> None:
        from kg_build_system.kernel.model.public.types import Array

        self.assertIs(kg_build_system.Array, Array)
        self.assertTrue(hasattr(kg_build_system, "BOOL"))
        self.assertTrue(hasattr(kg_build_system, "Timestamp"))

    def test_the_removed_types_alias_package_does_not_import(self) -> None:
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("kg_build_system.types")

    def test_the_canonical_entry_points_are_distinct(self) -> None:
        self.assertTrue(callable(kg_build_system.create_blueprint))
        self.assertTrue(callable(kg_build_system.compile))
        self.assertTrue(callable(kg_build_system.build))
        self.assertIsNot(kg_build_system.compile, compile_blueprint)

    def test_the_public_handles_name_their_artifacts(self) -> None:
        self.assertEqual(
            GraphBlueprint.__module__,
            "kg_build_system.declaration.blueprint.model.public.graph_blueprint",
        )
        self.assertEqual(
            WorkflowContractDTO.__module__,
            "kg_build_system.pipeline.contract.model.public.dto.contract",
        )
        self.assertEqual(
            BuildRuntime.__module__,
            "kg_build_system.pipeline.build.model.public.runtime",
        )
        self.assertEqual(
            WorkflowReport.__module__,
            "kg_build_system.pipeline.build.model.public.runtime",
        )
        self.assertEqual(create_blueprint.__module__, "kg_build_system.api")
        self.assertEqual(
            compile_blueprint.__module__,
            "kg_build_system.pipeline.compilation.service.public.compile",
        )
        self.assertEqual(
            build.__module__,
            "kg_build_system.pipeline.build.service.public.build",
        )


if __name__ == "__main__":
    unittest.main()
