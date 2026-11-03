"""Framework-internal interface of the graph-blueprint package.

The public handle is :class:`kg_build_system.declaration.blueprint.GraphBlueprint`.
Assembly, validation, the document codec and source rendering are consumed by
the composition root and by contract tests.
"""
from __future__ import annotations

from .service import (
    assemble_blueprint, blueprint_from_document, blueprint_to_document,
    blueprint_to_source, validate_blueprint,
)

__all__ = [
    "assemble_blueprint", "blueprint_from_document", "blueprint_to_document",
    "blueprint_to_source", "validate_blueprint",
]
