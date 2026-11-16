"""The public surface carries no Any and no erased Callable.

A public module is one under a package's ``model/public/`` or
``service/public/``, the root facade, the composition root ``api.py``, and the
``frontend`` package reached by ``execute(monitor=...)``.

The check is structural rather than textual: a docstring or a comment may say
``Any``; an annotation may not.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "kg_build_system"


def public_files() -> list[Path]:
    """Every module a graph author or a framework reviewer may depend on."""
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        if (
            "/model/public/" in relative
            or "/service/public/" in relative
            or relative in {"__init__.py", "api.py"}
            or relative.startswith("frontend/")
        ):
            files.append(path)
    return files


def is_any(node: ast.expr) -> bool:
    """Whether an annotation node names ``Any``."""
    return (isinstance(node, ast.Name) and node.id == "Any") or (
        isinstance(node, ast.Attribute) and node.attr == "Any"
    )


def is_erased_callable(node: ast.expr) -> bool:
    """Whether an annotation node is ``Callable[..., X]``."""
    if not isinstance(node, ast.Subscript):
        return False
    if not (isinstance(node.value, ast.Name) and node.value.id == "Callable"):
        return False
    return any(
        isinstance(item, ast.Constant) and item.value is Ellipsis
        for item in ast.walk(node.slice)
    )


def annotations(tree: ast.AST):
    """Yield every annotation expression in a module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.annotation is not None:
            yield node.annotation
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                yield node.returns
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def test_public_annotations_are_precise() -> None:
    offenders: list[str] = []
    for path in public_files():
        tree = ast.parse(path.read_text())
        for annotation in annotations(tree):
            for node in ast.walk(annotation):
                if is_any(node) or is_erased_callable(node):
                    relative = path.relative_to(ROOT).as_posix()
                    offenders.append(
                        f"{relative}:{node.lineno}: {ast.unparse(annotation)}"
                    )
    assert offenders == [], "\n".join(offenders)
