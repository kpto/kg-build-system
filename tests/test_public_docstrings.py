from __future__ import annotations

import inspect
import unittest
from importlib import import_module

import kg_build_system


SURFACES = (
    "kg_build_system",
    "kg_build_system.types",
    "kg_build_system.annotations",
    "kg_build_system.expressions",
    "kg_build_system.table",
    "kg_build_system.topology",
    "kg_build_system.binding",
    "kg_build_system.modules",
    "kg_build_system.workflow",
    "kg_build_system.compile",
    "kg_build_system.code_generation",
    "kg_build_system.types.interfaces",
    "kg_build_system.annotations.interfaces",
    "kg_build_system.expressions.interfaces",
    "kg_build_system.table.interfaces",
    "kg_build_system.topology.interfaces",
    "kg_build_system.binding.interfaces",
    "kg_build_system.modules.interfaces",
    "kg_build_system.workflow.interfaces",
    "kg_build_system.compile.interfaces",
    "kg_build_system.code_generation.interfaces",
    "kg_build_system.engines.interfaces",
    "kg_build_system.relational.interfaces",
)


class PublicDocstringTests(unittest.TestCase):
    def test_every_public_function_has_an_example(self) -> None:
        for surface in SURFACES:
            module = import_module(surface)
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(surface=surface, name=name):
                    document = inspect.getdoc(value) or ""
                    self.assertTrue(document, f"{surface}.{name} has no docstring")
                    self.assertIn(
                        "Example", document,
                        f"{surface}.{name} has no example in its docstring",
                    )

    def test_interface_functions_are_defined_in_the_interface(self) -> None:
        for surface in SURFACES:
            if not surface.endswith(".interfaces"):
                continue
            module = import_module(surface)
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(surface=surface, name=name):
                    self.assertEqual(
                        value.__module__, surface,
                        f"{surface}.{name} is a re-export, not an interface wrapper",
                    )

    def test_public_package_functions_are_not_implementation_reexports(self) -> None:
        for surface in SURFACES:
            if surface == "kg_build_system" or surface.endswith(".interfaces"):
                continue
            module = import_module(surface)
            allowed = {surface, f"{surface}.interfaces"}
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(surface=surface, name=name):
                    self.assertIn(
                        value.__module__, allowed,
                        f"{surface}.{name} comes from {value.__module__}",
                    )

    def test_top_level_functions_are_callable_wrappers(self) -> None:
        for name in kg_build_system.__all__:
            value = getattr(kg_build_system, name)
            if inspect.isfunction(value):
                self.assertTrue(value.__module__.startswith("kg_build_system"))


if __name__ == "__main__":
    unittest.main()
