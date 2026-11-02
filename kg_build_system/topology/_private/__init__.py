"""Private class-creation mechanics for topology declarations."""
from __future__ import annotations

from .class_creation import _prepare_topology_declaration
from .properties import (
    _PropertyDeclaration, _resolve_properties, attribute_docstring,
    declaration_name, make_property, member_name, snake_case,
)

__all__ = [
    "_PropertyDeclaration", "_prepare_topology_declaration",
    "_resolve_properties", "attribute_docstring", "declaration_name",
    "make_property", "member_name", "snake_case",
]
