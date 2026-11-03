"""Framework-internal interface of the graph-blueprint package.

The public handle is :class:`kg_build_system.declaration.blueprint.GraphBlueprint`.
Assembly, validation, the document codec and source rendering load on first use;
importing this package does not import a service module.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .service import (
        assemble_blueprint,
        blueprint_from_document,
        blueprint_to_document,
        blueprint_to_source,
        validate_blueprint,
    )


def __getattr__(name: str) -> Any:
    """Load one internal service name on first use."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from . import service

    return getattr(service, name)


__all__ = [
    "assemble_blueprint", "blueprint_from_document", "blueprint_to_document",
    "blueprint_to_source", "validate_blueprint",
]
