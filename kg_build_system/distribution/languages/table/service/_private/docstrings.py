"""Attribute documentation recovered from declaration source.

Python evaluates a string literal below an assignment and then discards it, so
the object model never carries it. It remains present in the module source, and
a declaration descriptor can recover it while the declaring class is being
created — which is the only moment the declaring class is unambiguously known.

``inspect`` locates the class, which covers declarations nested in functions,
other classes, and control flow alike. Parsing that block rather than scanning
it is what attaches a literal to the member above it instead of to whatever
statement happens to precede it.

Source availability is therefore part of declaration semantics: a class whose
source cannot be read resolves no attribute documentation, exactly as if the
docstrings had been omitted.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Any


def _assigned_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    return None


def _attribute_documents(body: list[ast.stmt]) -> dict[str, str]:
    """Map each assigned attribute to a string literal written directly below it."""
    documents: dict[str, str] = {}
    for statement, following in zip(body, body[1:]):
        name = _assigned_name(statement)
        if name is None or not isinstance(following, ast.Expr):
            continue
        value = following.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        text = inspect.cleandoc(value.value)
        if text:
            documents[name] = text
    return documents


def attribute_docstring(owner: type[Any], attribute: str) -> str | None:
    """The documentation written directly below ``owner.attribute``, if any."""
    try:
        source = textwrap.dedent(inspect.getsource(owner))
    except (OSError, TypeError, IndentationError):
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    declaration = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef)), None
    )
    if declaration is None:
        return None
    return _attribute_documents(declaration.body).get(attribute)


__all__ = ["attribute_docstring"]
