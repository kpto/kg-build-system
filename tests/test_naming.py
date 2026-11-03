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

    def test_public_and_internal_all_do_not_export_private_names(self) -> None:
        for path in _framework_files():
            if path.name != "__init__.py":
                continue
            relative = path.relative_to(ROOT)
            if not ({"public", "internal"} & set(relative.parts)):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                if not any(getattr(target, "id", None) == "__all__" for target in node.targets):
                    continue
                try:
                    values = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    continue
                private = [
                    value for value in values
                    if isinstance(value, str)
                    and value.startswith("_")
                    and not (value.startswith("__") and value.endswith("__"))
                ]
                self.assertEqual(
                    private, [],
                    f"{path} exports private names in __all__: {private}",
                )

    def test_no_cross_package_private_import(self) -> None:
        def leaf(parts: tuple[str, ...]) -> tuple[str, ...]:
            if parts[0] == "declaration" and len(parts) > 2 and parts[1] in {"foundations", "languages"}:
                return parts[:3]
            if parts[0] == "pipeline" and len(parts) > 1:
                return parts[:2]
            return parts[:1]

        for path in _framework_files():
            relative = path.relative_to(ROOT)
            own = leaf(relative.parts)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level == 0:
                    continue
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                target = base.joinpath(*(node.module or "").split("."))
                try:
                    target_parts = target.relative_to(ROOT).parts
                except ValueError:
                    continue
                if leaf(target_parts) == own:
                    continue
                names = [
                    alias.name for alias in node.names
                    if alias.name.startswith("_")
                    and not (alias.name.startswith("__") and alias.name.endswith("__"))
                ]
                self.assertEqual(
                    names, [],
                    f"{path}:{node.lineno} imports private names {names} from {node.module}",
                )

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
