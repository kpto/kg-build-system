from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
GROUPS = (
    "kernel",
    "distribution",
    "generation",
    "cli",
)
LEAVES = (
    "kernel",
    "distribution",
    "distribution/languages/annotations",
    "distribution/languages/expressions",
    "distribution/languages/data",
    "distribution/languages/topology",
    "distribution/languages/binding",
    "distribution/interpreter",
    "distribution/modules/core",
    "distribution/modules/deduplication",
    "distribution/modules/merging",
    "distribution/modules/conflict_validation",
    "distribution/modules/runtime",
    "distribution/modules/duckdb",
    "distribution/modules/python",
    "distribution/modules/file",
    "distribution/modules/meta_graph",
    "distribution/modules/neo4j",
    "generation/code_generation",
    "cli",
)
LEAF_PARTS = {tuple(leaf.split("/")): leaf for leaf in LEAVES}
INTERFACE_SURFACES = (
    "model/public",
    "model/internal",
    "service/public",
    "service/internal",
)


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


def _leaf(parts: list[str]) -> str | None:
    for leaf_parts in sorted(LEAF_PARTS, key=len, reverse=True):
        if tuple(parts[: len(leaf_parts)]) == leaf_parts:
            return LEAF_PARTS[leaf_parts]
    return None


def _owner(path: Path) -> str | None:
    return _leaf(list(path.relative_to(ROOT).parts))


def _surface(path: Path) -> str | None:
    relative = path.relative_to(ROOT)
    parts = relative.parts
    for leaf in LEAVES:
        leaf_parts = tuple(leaf.split("/"))
        if tuple(parts[: len(leaf_parts)]) == leaf_parts:
            tail = parts[len(leaf_parts) :]
            if len(tail) >= 2 and tail[0] in {"model", "service"}:
                return f"{tail[0]}/{tail[1]}"
            return None
    return None


def _is_dto_module(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    parts = relative.parts
    if "model" in parts and "public" in parts:
        return True
    if "model" in parts and "internal" in parts:
        return (
            "dto" in parts
            or path.stem == "dto"
            or path.name.endswith("_dto.py")
        )
    return path.stem == "dto" or path.name.endswith("_dto.py")


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        parts = None
        names: list[str] = []
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                try:
                    relative = list(base.relative_to(ROOT).parts)
                except ValueError:
                    continue
                parts = relative + (node.module.split(".") if node.module else [])
            elif node.module and node.module.startswith("kg_build_system."):
                parts = node.module.split(".")[1:]
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("kg_build_system."):
                    yield alias.name.split(".")[1:], line, []
            continue
        if parts is not None:
            yield parts, line, names


class NamingTests(unittest.TestCase):
    def test_interfaces_define_no_single_underscore_helpers(self) -> None:
        for leaf in LEAVES:
            for surface in INTERFACE_SURFACES:
                directory = ROOT / leaf / surface
                if not directory.is_dir():
                    continue
                for path in directory.rglob("*.py"):
                    if "__pycache__" in path.parts:
                        continue
                    for name, line in _definitions(path):
                        if not name.startswith("_"):
                            continue
                        if name.startswith("__") and name.endswith("__"):
                            continue
                        self.fail(
                            f"{path}:{line} defines private helper {name!r} in "
                            f"{surface}; move it to _private"
                        )

    def test_dto_classes_live_in_a_model_dto_module(self) -> None:
        for path in _framework_files():
            for name, line in _classes(path):
                if name.endswith("DTO") and not _is_dto_module(path):
                    self.fail(
                        f"{path}:{line} declares DTO {name!r} outside a model DTO module"
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

    def test_no_cross_package_underscore_import(self) -> None:
        for path in _framework_files():
            owner = _owner(path)
            for parts, line, names in _imports(path):
                target = _leaf(parts)
                if target is None or target == owner:
                    continue
                module_names = [
                    part for part in parts
                    if part.startswith("_")
                    and not (part.startswith("__") and part.endswith("__"))
                ]
                imported_names = [
                    name for name in names
                    if name.startswith("_")
                    and not (name.startswith("__") and name.endswith("__"))
                ]
                self.assertEqual(
                    (module_names, imported_names),
                    ([], []),
                    f"{path}:{line} imports private names "
                    f"{module_names + imported_names} from {'.'.join(parts)}",
                )

    def test_an_instruction_kind_is_a_tuple_of_strings(self) -> None:
        from kg_build_system.kernel import Instruction

        instruction = Instruction(("sql", "duckdb"), None)
        self.assertIsInstance(instruction.kind, tuple)
        self.assertTrue(instruction.kind)
        self.assertTrue(all(isinstance(part, str) for part in instruction.kind))

    def test_no_public_module_keeps_the_removed_contract_or_module_name(
        self,
    ) -> None:
        for path in (ROOT / "kernel").rglob("*.py"):
            self.assertNotEqual(path.name, "contract_dto.py", str(path))
            self.assertFalse(
                path.parent.name == "public" and path.name == "module.py",
                str(path),
            )
        for path in (ROOT / "distribution").rglob("*.py"):
            self.assertNotEqual(path.name, "contract_dto.py", str(path))
            self.assertFalse(
                path.parent.name == "public" and path.name == "module.py",
                str(path),
            )


if __name__ == "__main__":
    unittest.main()
