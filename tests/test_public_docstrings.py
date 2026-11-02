from __future__ import annotations

import inspect
import unittest
from importlib import import_module

import kg_build_system


PACKAGES = (
    "kg_build_system.kernel",
    "kg_build_system.types",
    "kg_build_system.annotations",
    "kg_build_system.expressions",
    "kg_build_system.table",
    "kg_build_system.topology",
    "kg_build_system.binding",
    "kg_build_system.relational",
    "kg_build_system.engines",
    "kg_build_system.compile",
    "kg_build_system.workflow",
    "kg_build_system.modules",
    "kg_build_system.code_generation",
    "kg_build_system.cli",
)


def _public_module(package: str) -> object:
    return import_module(f"{package}.public")


def _framework_defined(value: object, module: str) -> bool:
    owner = getattr(value, "__module__", "")
    return isinstance(owner, str) and owner.startswith(module)


class PublicDocstringTests(unittest.TestCase):
    def test_every_public_function_has_an_example(self) -> None:
        for package in PACKAGES:
            module = _public_module(package)
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(surface=f"{package}.public", name=name):
                    document = inspect.getdoc(value) or ""
                    self.assertTrue(document, f"{package}.public.{name} has no docstring")
                    self.assertIn(
                        "Example", document,
                        f"{package}.public.{name} has no example in its docstring",
                    )
                    self.assertTrue(
                        _framework_defined(value, f"{package}.public"),
                        f"{package}.public.{name} is a re-export from "
                        f"{getattr(value, '__module__', '?')}",
                    )

    def test_every_public_class_method_has_an_example(self) -> None:
        for package in PACKAGES:
            module = _public_module(package)
            for class_name in getattr(module, "__all__", ()):
                cls = getattr(module, class_name)
                if not inspect.isclass(cls) or not _framework_defined(
                    cls, f"{package}.public"
                ):
                    continue
                for name, value in vars(cls).items():
                    if name.startswith("_") or name == "__init__":
                        continue
                    if isinstance(value, (classmethod, staticmethod)):
                        value = value.__func__
                    if not inspect.isfunction(value):
                        continue
                    with self.subTest(surface=f"{package}.public", name=f"{class_name}.{name}"):
                        self.assertIn(
                            "Example", inspect.getdoc(value) or "",
                            f"{package}.public.{class_name}.{name} has no example",
                        )

    def test_every_package_facade_function_comes_from_public(self) -> None:
        for package in PACKAGES:
            module = import_module(package)
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(package=package, name=name):
                    self.assertTrue(
                        value.__module__.startswith(f"{package}.public")
                        or value.__module__ == package,
                        f"{package}.{name} comes from {value.__module__}",
                    )
                    self.assertNotIn("._private", value.__module__)

    def test_every_internal_function_is_documented_for_developers(self) -> None:
        for package in PACKAGES:
            module = import_module(f"{package}.internal")
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(package=package, name=name):
                    self.assertTrue(
                        (inspect.getdoc(value) or "").strip(),
                        f"{package}.internal.{name} has no developer docstring",
                    )

    def test_top_level_functions_are_callable(self) -> None:
        for name in kg_build_system.__all__:
            value = getattr(kg_build_system, name)
            if inspect.isfunction(value):
                self.assertTrue(callable(value))


if __name__ == "__main__":
    unittest.main()
