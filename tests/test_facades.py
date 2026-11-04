from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent


def _is_all_assignment(node: ast.stmt) -> bool:
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            return False
        target = node.targets[0]
    elif isinstance(node, ast.AnnAssign):
        target = node.target
    else:
        return False
    return (
        isinstance(target, ast.Name)
        and target.id == "__all__"
        and isinstance(node.value, (ast.List, ast.Tuple))
        and all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in node.value.elts
        )
    )


def _is_import_groups(node: ast.stmt) -> bool:
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return False
        target = node.targets[0]
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        target = node.target
    else:
        return False
    if target.id != "_GROUPS" or not isinstance(node.value, ast.Dict):
        return False
    for key, value in zip(node.value.keys, node.value.values):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            return False
        if not isinstance(value, (ast.Tuple, ast.List)):
            return False
        if not all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in value.elts
        ):
            return False
    return True


def _is_import_machinery(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.FunctionDef)
        and node.name in {"__getattr__", "__dir__"}
    )


def _is_type_checking_block(node: ast.stmt) -> bool:
    if not isinstance(node, ast.If) or node.orelse:
        return False
    if "TYPE_CHECKING" not in ast.unparse(node.test):
        return False
    return all(
        isinstance(child, (ast.Import, ast.ImportFrom))
        or (
            isinstance(child, ast.Expr)
            and isinstance(child.value, ast.Constant)
            and isinstance(child.value.value, str)
        )
        for child in node.body
    )


class FacadeTests(unittest.TestCase):
    def test_every_init_contains_only_import_machinery(self) -> None:
        for path in sorted(ROOT.rglob("__init__.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        continue
                    if (
                        isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    ):
                        continue
                    if _is_all_assignment(node):
                        continue
                    if _is_import_groups(node):
                        continue
                    if _is_import_machinery(node):
                        continue
                    if _is_type_checking_block(node):
                        continue
                    self.fail(
                        f"{path}:{node.lineno} has a forbidden facade statement "
                        f"{type(node).__name__}: {ast.unparse(node)}"
                    )


    def test_the_literal_export_table_matches_the_lazy_groups(self) -> None:
        groups = kg_build_system._GROUPS
        expected = {
            name for names in groups.values() for name in names
        }
        self.assertEqual(set(kg_build_system.__all__), expected)
        self.assertEqual(len(kg_build_system.__all__), len(expected))

    def test_every_export_is_resolvable(self) -> None:
        for name in kg_build_system.__all__:
            with self.subTest(name=name):
                self.assertIsNotNone(getattr(kg_build_system, name))


if __name__ == "__main__":
    unittest.main()
