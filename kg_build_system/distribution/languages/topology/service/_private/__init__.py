"""Private class-creation mechanics for topology declarations."""
from __future__ import annotations

from .class_creation import prepare_topology_declaration, make_endpoint
from ...model._private.properties import (
    _PropertyDeclaration, _resolve_properties, attribute_docstring,
    declaration_name, make_property, member_name, snake_case,
)

__all__ = [
    "_PropertyDeclaration", "prepare_topology_declaration",
    "_resolve_properties", "attribute_docstring", "declaration_name",
    "make_endpoint", "make_property", "member_name", "snake_case",
]
