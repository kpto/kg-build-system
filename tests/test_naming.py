from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
GROUPS = (
    "kernel",
    "declaration",
    "pipeline",
    "distribution",
    "generation",
    "cli",
)
# No framework definition may carry the ``IR`` suffix.


def _definitions(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node.lineno


def _classes(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield node.name, node.lineno


def _framework_files():
    for group in GROUPS:
        for path in (ROOT / group).rglob("*.py"):
            if "__pycache__" not in path.parts:
                yield path


def _is_dto_module(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        any(part == "dto" for part in relative.parts[:-1])
        or path.stem == "dto"
        or path.name.endswith("_dto.py")
    )


class NamingTests(unittest.TestCase):
    def test_no_definition_uses_the_lowering_verb(self) -> None:
        for path in _framework_files():
            for name, line in _definitions(path):
                if "lower" in name.lower():
                    self.fail(f"{path}:{line} defines the lowering name {name!r}")

    def test_no_definition_uses_ir(self) -> None:
        found: set[tuple[str, str]] = set()
        for path in _framework_files():
            for name, line in _definitions(path):
                if name == "IR" or name.endswith("IR"):
                    relative = path.relative_to(ROOT).as_posix()
                    found.add((relative, f"{name} at {line}"))

        self.assertEqual(found, set())

    def test_dto_classes_live_in_a_dto_module(self) -> None:
        for path in _framework_files():
            for name, line in _classes(path):
                if name.endswith("DTO") and not _is_dto_module(path):
                    self.fail(f"{path}:{line} declares DTO {name!r} outside a DTO module")

    def test_plans_and_generated_models_are_not_dtos(self) -> None:
        for path in _framework_files():
            for name, line in _classes(path):
                lowered = name.lower()
                if "plan" in lowered or "generated" in lowered:
                    self.assertFalse(
                        name.endswith("DTO"),
                        f"{path}:{line} declares {name!r} as a DTO",
                    )


if __name__ == "__main__":
    unittest.main()
