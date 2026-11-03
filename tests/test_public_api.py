from __future__ import annotations

import importlib
import inspect
import unittest

import kg_build_system
from kg_build_system import (
    BuildRuntime,
    GraphBlueprint,
    WorkflowPlan,
    WorkflowReport,
    compile,
    create_blueprint,
    execute,
)


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

    def test_execute_replaces_the_old_build_name(self) -> None:
        self.assertTrue(callable(kg_build_system.execute))
        self.assertFalse(hasattr(kg_build_system, "build"))

    def test_the_canonical_entry_points_are_distinct(self) -> None:
        self.assertTrue(callable(kg_build_system.create_blueprint))
        self.assertTrue(callable(kg_build_system.compile))
        self.assertTrue(callable(kg_build_system.execute))
        self.assertIsNot(kg_build_system.compile, kg_build_system.execute)

    def test_the_removed_layers_do_not_import(self) -> None:
        for removed in ("declaration", "pipeline"):
            name = f"kg_build_system.{removed}"
            with self.subTest(name=name):
                with self.assertRaises(ModuleNotFoundError):
                    importlib.import_module(name)

    def test_the_public_handles_name_their_artifacts(self) -> None:
        self.assertEqual(
            GraphBlueprint.__module__,
            "kg_build_system.distribution.interpreter.model.public.graph_blueprint",
        )
        self.assertEqual(
            WorkflowPlan.__module__,
            "kg_build_system.kernel.model.public.workflow",
        )
        self.assertEqual(
            WorkflowReport.__module__,
            "kg_build_system.kernel.model.public.runtime",
        )
        self.assertEqual(
            BuildRuntime.__module__,
            "kg_build_system.distribution.model.public.runtime",
        )
        self.assertEqual(create_blueprint.__module__, "kg_build_system.api")
        self.assertEqual(compile.__module__, "kg_build_system.api")
        self.assertEqual(execute.__module__, "kg_build_system.api")

    def test_the_root_exports_the_workflow_handles(self) -> None:
        for name in (
            "compile",
            "execute",
            "create_blueprint",
            "WorkflowPlan",
            "WorkflowReport",
            "BuildRuntime",
            "GraphBlueprint",
        ):
            with self.subTest(name=name):
                self.assertIn(name, kg_build_system.__all__)


if __name__ == "__main__":
    unittest.main()
