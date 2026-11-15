"""The reference project obeys the declared project-structure practice."""
from __future__ import annotations

import ast
import dataclasses
import importlib
import unittest
from pathlib import Path

from kg_build_system import (
    Asset,
    DerivedRelation,
    Edge,
    Graph,
    Node,
    SourceRelation,
    create_blueprint,
)
from kg_build_system.distribution.languages.binding import EdgeBinding, NodeBinding
from kg_build_system.distribution.languages.data.model.internal import RowScanDTO

ROOT = Path(__file__).parent.parent / "reference_project"
PACKAGE = "reference_project"


def _modules() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and "build" not in path.parts
    )


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT.parent).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _initializer_modules() -> set[str]:
    return {
        _module_name(path)
        for path in _modules()
        if path.name == "__init__.py"
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    package = _module_name(path)
    if path.name != "__init__.py":
        package = package.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base = (
                    parts[: len(parts) - (node.level - 1)]
                    if node.level > 1 else parts
                )
                prefix = ".".join(base)
                found.add(f"{prefix}.{node.module}" if node.module else prefix)
            elif node.module:
                found.add(node.module)
    return found


def _defined_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _declaration_sites() -> dict[str, set[str]]:
    """Map each declaration's defining module to the public names it declares.

    A class names its site through ``__module__``; a binding names it through
    the stable reference to its row callable. Re-exports in a facade therefore
    resolve to the definition site, not to the facade.
    """
    bases = (Asset, DerivedRelation, Edge, Graph, Node, SourceRelation)
    sites: dict[str, set[str]] = {}
    for path in _modules():
        module = importlib.import_module(_module_name(path))
        for name, value in vars(module).items():
            if name.startswith("_"):
                continue
            site: str | None = None
            if isinstance(value, (NodeBinding, EdgeBinding)):
                if value.python_ref is not None:
                    site = value.python_ref.module
                elif path.name != "__init__.py":
                    site = module.__name__
            elif isinstance(value, type) and issubclass(value, bases):
                site = value.__module__
            if site is None or not site.startswith(f"{PACKAGE}."):
                continue
            sites.setdefault(site, set()).add(name)
    return sites


def _scans(value: object) -> set[str]:
    found: set[str] = set()
    stack = [value]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, RowScanDTO):
            found.add(current.relation.name)
        if dataclasses.is_dataclass(current):
            stack.extend(
                getattr(current, field.name) for field in dataclasses.fields(current)
            )
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return found


class FacadeTests(unittest.TestCase):
    def test_no_initializer_declares_a_class_or_function(self) -> None:
        offenders = {
            str(path.relative_to(ROOT)): _defined_names(path)
            for path in _modules()
            if path.name == "__init__.py" and _defined_names(path)
        }
        self.assertEqual(offenders, {})


class DeclarationSiteTests(unittest.TestCase):
    def test_each_public_declaration_has_one_file(self) -> None:
        sites = _declaration_sites()
        for axis in (
            f"{PACKAGE}.asset.",
            f"{PACKAGE}.graph.",
            f"{PACKAGE}.relation.source.",
            f"{PACKAGE}.relation.derived.",
            f"{PACKAGE}.binding.",
        ):
            with self.subTest(axis=axis):
                self.assertTrue(
                    any(module.startswith(axis) for module in sites),
                    f"no declaration found under {axis}",
                )
        offenders = {
            module: sorted(names)
            for module, names in sites.items()
            if len(names) != 1
        }
        self.assertEqual(offenders, {})

    def test_declaration_site_is_not_an_initializer(self) -> None:
        initializers = _initializer_modules()
        offenders = sorted(
            f"{module} declares {sorted(names)}"
            for module, names in _declaration_sites().items()
            if module in initializers
        )
        self.assertEqual(offenders, [])


class StagePrivacyTests(unittest.TestCase):
    def test_no_module_outside_the_package_imports_a_stage(self) -> None:
        offenders: list[str] = []
        for path in _modules():
            module = _module_name(path)
            for imported in _imports(path):
                if ".relation.derived." not in imported or "._" not in imported:
                    continue
                derived = imported.split(".relation.derived.", 1)[1].split(".", 1)[0]
                if not module.startswith(
                    f"{PACKAGE}.relation.derived.{derived}."
                ):
                    offenders.append(f"{module} imports {imported}")
        self.assertEqual(offenders, [])

    def test_no_binding_reads_a_stage(self) -> None:
        blueprint = create_blueprint(namespace_path=ROOT)
        internal = {
            relation.name
            for relation in blueprint.data.derived_relations
            if relation.visibility == "internal"
        }
        self.assertTrue(internal)
        offenders: list[str] = []
        for binding in blueprint.bindings:
            rows = getattr(binding, "rows", None)
            offenders.extend(
                f"{binding.component} reads stage {name}"
                for name in _scans(rows) & internal
            )
        self.assertEqual(offenders, [])


class DependencyDirectionTests(unittest.TestCase):
    def test_the_axes_do_not_import_each_other(self) -> None:
        binding_modules = {
            module for module in _declaration_sites()
            if module.startswith(f"{PACKAGE}.binding.")
        }
        offenders: list[str] = []
        for path in _modules():
            module = _module_name(path)
            imported = _imports(path)
            if module == f"{PACKAGE}.graph" or module.startswith(f"{PACKAGE}.graph."):
                forbidden = (f"{PACKAGE}.relation", f"{PACKAGE}.binding")
                offenders.extend(
                    f"{module} imports {edge}"
                    for edge in imported if edge.startswith(forbidden)
                )
            elif module == f"{PACKAGE}.relation" or module.startswith(
                f"{PACKAGE}.relation."
            ):
                forbidden = (f"{PACKAGE}.graph", f"{PACKAGE}.binding")
                offenders.extend(
                    f"{module} imports {edge}"
                    for edge in imported if edge.startswith(forbidden)
                )
            if module in binding_modules:
                if not any(edge.startswith(f"{PACKAGE}.graph") for edge in imported):
                    offenders.append(f"{module} does not import graph/")
                if not any(edge.startswith(f"{PACKAGE}.relation") for edge in imported):
                    offenders.append(f"{module} does not import relation/")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
