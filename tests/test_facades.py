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
    def test_every_init_is_docstring_imports_type_checking_and_all(self) -> None:
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
                    if _is_type_checking_block(node):
                        continue
                    self.fail(
                        f"{path}:{node.lineno} has a forbidden facade statement "
                        f"{type(node).__name__}: {ast.unparse(node)}"
                    )


if __name__ == "__main__":
    unittest.main()
