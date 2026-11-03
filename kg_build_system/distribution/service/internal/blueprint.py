"""Thin blueprint-context wrapper over the private implementation."""
from __future__ import annotations

from typing import Any

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint


def blueprint_from_context(context: Any) -> GraphBlueprint:
    """The graph blueprint carried by one compilation context."""
    from .._private.service.blueprint import (
        blueprint_from_context as implementation,
    )

    return implementation(context)


__all__ = ["blueprint_from_context"]
