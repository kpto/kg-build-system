from __future__ import annotations

import inspect
import unittest
from importlib import import_module

import kg_build_system


PACKAGES = (
    "kg_build_system.kernel",
    "kg_build_system.declaration.foundations.annotations",
    "kg_build_system.declaration.foundations.expressions",
    "kg_build_system.declaration.languages.table",
    "kg_build_system.declaration.languages.topology",
    "kg_build_system.declaration.languages.binding",
    "kg_build_system.declaration.blueprint",
    "kg_build_system.pipeline.contract",
    "kg_build_system.pipeline.compile",
    "kg_build_system.pipeline.execution",
    "kg_build_system.distribution",
    "kg_build_system.generation.code_generation",
    "kg_build_system.cli",
)
PUBLIC_SURFACES = ("model.public", "service.public")
INTERNAL_SURFACES = ("model.internal", "service.internal")
# Public helpers that are still exported without an ``Example`` block. They are
# framework defects, kept here so the test states them once instead of weakening
# the check for every public function.
KNOWN_MISSING_FUNCTION_EXAMPLES = {
    (
        "kg_build_system.declaration.languages.table.model.public.declarations",
        "is_concrete_table",
    ),
    (
        "kg_build_system.declaration.languages.table.model.public.declarations",
        "is_table_group",
    ),
    ("kg_build_system.distribution.model.public.artifacts", "component_kind"),
    ("kg_build_system.distribution.model.public.artifacts", "graph_components"),
    (
        "kg_build_system.distribution.model.public.artifacts",
        "graph_record_components",
    ),
}
# Public class methods still missing examples. These are reported as framework
# defects; the exception names the exact method rather than the whole class.
KNOWN_MISSING_METHOD_EXAMPLES = {
    (
        "kg_build_system.declaration.foundations.expressions.model.public.selections.value",
        "ValueSelection",
        "require_expression",
    ),
    *{
        (
            "kg_build_system.distribution.model.public.artifacts",
            "CoreArtifactTypes",
            method,
        )
        for method in (
            "graph_records",
            "binding",
            "table",
            "projection",
            "row_source",
            "graph_record_identity",
            "is_graph_records",
        )
    },
    *{
        (
            f"kg_build_system.distribution.service.public.modules.{module}",
            module_class,
            method,
        )
        for module, module_class in (
            ("conflict_validation", "RejectConflictingNonNullValuesModule"),
            ("core", "CoreModule"),
            ("deduplication", "CollapseExactDuplicatesModule"),
            ("file", "FileModule"),
            ("merging", "MergeCompatibleFactsModule"),
            ("meta_graph", "MetaGraphModule"),
            ("neo4j", "Neo4jModule"),
        )
        for method in ("compiler", "executor")
    },
}


def _module(package: str, surface: str):
    try:
        return import_module(f"{package}.{surface}")
    except ModuleNotFoundError:
        return None


def _accepted_owner(value: object, package: str) -> bool:
    owner = getattr(value, "__module__", "")
    if not isinstance(owner, str):
        return False
    return (
        owner == package
        or owner.startswith(f"{package}.model.public")
        or owner.startswith(f"{package}.service.public")
    )


def _public_functions(package: str):
    for surface in PUBLIC_SURFACES:
        module = _module(package, surface)
        if module is None:
            continue
        for name in getattr(module, "__all__", ()):
            value = getattr(module, name)
            if not inspect.isfunction(value):
                continue
            if (value.__module__, name) in KNOWN_MISSING_FUNCTION_EXAMPLES:
                continue
            yield f"{package}.{surface}", name, value


def _public_classes(package: str):
    for surface in PUBLIC_SURFACES:
        module = _module(package, surface)
        if module is None:
            continue
        for name in getattr(module, "__all__", ()):
            value = getattr(module, name)
            if not inspect.isclass(value):
                continue
            if not getattr(value, "__module__", "").startswith(package):
                continue
            yield f"{package}.{surface}", name, value


class PublicDocstringTests(unittest.TestCase):
    def test_every_public_function_has_an_example(self) -> None:
        for package in PACKAGES:
            for surface, name, value in _public_functions(package):
                with self.subTest(surface=surface, name=name):
                    document = inspect.getdoc(value) or ""
                    self.assertTrue(document, f"{surface}.{name} has no docstring")
                    self.assertIn(
                        "Example",
                        document,
                        f"{surface}.{name} has no example in its docstring",
                    )

    def test_every_public_class_method_has_an_example(self) -> None:
        for package in PACKAGES:
            for surface, class_name, cls in _public_classes(package):
                for name, value in vars(cls).items():
                    if name.startswith("_") or name == "__init__":
                        continue
                    if isinstance(value, (classmethod, staticmethod)):
                        value = value.__func__
                    if not inspect.isfunction(value):
                        continue
                    if (
                        cls.__module__,
                        class_name,
                        name,
                    ) in KNOWN_MISSING_METHOD_EXAMPLES:
                        continue
                    with self.subTest(
                        surface=surface, name=f"{class_name}.{name}",
                    ):
                        self.assertIn(
                            "Example",
                            inspect.getdoc(value) or "",
                            f"{surface}.{class_name}.{name} has no example",
                        )

    def test_every_facade_function_comes_from_a_public_surface(self) -> None:
        for package in PACKAGES:
            module = import_module(package)
            for name in getattr(module, "__all__", ()):
                value = getattr(module, name)
                if not inspect.isfunction(value):
                    continue
                with self.subTest(package=package, name=name):
                    self.assertTrue(
                        _accepted_owner(value, package),
                        f"{package}.{name} comes from {value.__module__}",
                    )

    def test_every_internal_function_is_documented_for_developers(self) -> None:
        for package in PACKAGES:
            for surface in INTERNAL_SURFACES:
                try:
                    module = _module(package, surface)
                except ModuleNotFoundError:
                    continue
                for name in getattr(module, "__all__", ()):
                    value = getattr(module, name)
                    if not inspect.isfunction(value):
                        continue
                    with self.subTest(package=package, surface=surface, name=name):
                        self.assertTrue(
                            (inspect.getdoc(value) or "").strip(),
                            f"{package}.{surface}.{name} has no developer docstring",
                        )

    def test_top_level_functions_are_callable(self) -> None:
        for name in kg_build_system.__all__:
            value = getattr(kg_build_system, name)
            if inspect.isfunction(value):
                self.assertTrue(callable(value))

    def test_top_level_entry_points_are_wrappers(self) -> None:
        expected = {
            "create_blueprint": "kg_build_system.api",
            "compile": "kg_build_system.api",
            "execute": "kg_build_system.pipeline.execution.service.public.execute",
        }
        for name, module in expected.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(kg_build_system, name).__module__, module)


if __name__ == "__main__":
    unittest.main()
