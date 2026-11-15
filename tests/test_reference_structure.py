"""The reference project obeys the declared project-structure practice."""
from __future__ import annotations

import ast
import dataclasses
import importlib
import unittest
from pathlib import Path

from kg_build_system import create_blueprint
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


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _defined_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


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

    def test_every_module_is_importable_without_starting_a_build(self) -> None:
        for path in _modules():
            if path.name == "__init__.py":
                continue
            importlib.import_module(_module_name(path))


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
        offenders: list[str] = []
        for path in _modules():
            module = _module_name(path)
            if module == f"{PACKAGE}.graph" or module.startswith(f"{PACKAGE}.graph."):
                forbidden = (f"{PACKAGE}.relation", f"{PACKAGE}.binding")
            elif module == f"{PACKAGE}.relation" or module.startswith(
                f"{PACKAGE}.relation."
            ):
                forbidden = (f"{PACKAGE}.graph", f"{PACKAGE}.binding")
            else:
                continue
            for imported in _imports(path):
                if imported.startswith(forbidden):
                    offenders.append(f"{module} imports {imported}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
