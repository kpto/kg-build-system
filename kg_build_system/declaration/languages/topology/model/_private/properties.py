"""Property-slot mechanics used while a declaration class is created."""
from __future__ import annotations

import ast
import inspect
import re
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, get_args, get_type_hints

from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)
from kg_build_system.declaration.foundations.annotations.service.internal import (
    annotation_tuple,
)
from kg_build_system.kernel.service.internal.types import (
    normalize_type, require_graph_property,
)
from ..internal.model.metadata import PropertyDeclaration

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class _PropertyDeclaration(Generic[T]):
    """The descriptor an author assigns to a property slot."""

    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attr: str = ""

    def __set_name__(self, owner: type[Any], attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None:
            object.__setattr__(self, "name", member_name(attr))
        if self.description is None:
            object.__setattr__(
                self, "description", attribute_docstring(owner, attr),
            )


def make_property(
    *, name: str | None = None, description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Any:
    """Build the descriptor assigned to a property slot."""
    if name is not None and not name:
        raise ValueError("property names must be non-empty")
    return _PropertyDeclaration[Any](
        name=name,
        description=description,
        annotations=annotation_tuple(list(annotations)),
    )


def snake_case(value: str) -> str:
    """Convert a Python identifier to the portable external-name convention."""
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", value)
    value = re.sub(r"([0-9])([A-Za-z])", r"\1_\2", value)
    return value.lower()


def member_name(attribute: str) -> str:
    """Infer an external member name, reserving one trailing underscore."""
    return snake_case(attribute[:-1] if attribute.endswith("_") else attribute)


def declaration_name(class_name: str, *, suffixes: tuple[str, ...] = ()) -> str:
    """Infer a declaration name, removing one matching semantic suffix."""
    stem = class_name
    for suffix in suffixes:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    if not stem:
        raise ValueError(
            f"{class_name!r} has no name after removing its declaration suffix"
        )
    return snake_case(stem)


def _assigned_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    return None


def _attribute_documents(body: list[ast.stmt]) -> dict[str, str]:
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


def _resolve_properties(cls: type[Any]) -> tuple[PropertyDeclaration, ...]:
    """Resolve property declarations over the MRO, once, in declaration order."""
    declarations: dict[str, tuple[type[Any], _PropertyDeclaration[Any]]] = {}
    for base in reversed(cls.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, _PropertyDeclaration):
                declarations[attribute] = (base, value)
            elif attribute in declarations:
                del declarations[attribute]

    hints = get_type_hints(cls)
    external: dict[str, str] = {}
    resolved: list[PropertyDeclaration] = []
    for attribute, (owner, declaration) in declarations.items():
        arguments = get_args(hints.get(attribute, Any))
        if len(arguments) != 1:
            raise TypeError(
                f"{cls.__name__}.{attribute} must be annotated as PropertySlot[T]"
            )
        authoring_type = arguments[0]
        logical_type = require_graph_property(
            normalize_type(authoring_type), context=f"{cls.__name__}.{attribute}"
        )
        name = declaration.name
        if name is None:
            name = member_name(attribute)
        description = declaration.description
        if description is None:
            description = attribute_docstring(owner, attribute)
        if name in external:
            raise TypeError(
                f"{cls.__name__} properties {external[name]!r} and {attribute!r} "
                f"share external name {name!r}"
            )
        external[name] = attribute
        resolved.append(PropertyDeclaration(
            attribute=attribute,
            name=name,
            logical_type=logical_type,
            authoring_type=authoring_type,
            description=description,
            annotations=tuple(declaration.annotations),
        ))
    return tuple(resolved)


__all__ = [
    "_PropertyDeclaration", "_resolve_properties", "attribute_docstring",
    "declaration_name", "make_property", "member_name", "snake_case",
]
