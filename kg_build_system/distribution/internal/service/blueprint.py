"""Read the graph blueprint a distribution module compiler was given."""
from __future__ import annotations

from typing import Any

from ....declaration.blueprint.public import GraphBlueprint


def blueprint_from_context(context: Any) -> GraphBlueprint:
    """The graph blueprint carried by one compilation context."""
    blueprint = getattr(context, "blueprint", None)
    if not isinstance(blueprint, GraphBlueprint):
        raise ValueError("module compilation requires a GraphBlueprint")
    return blueprint


__all__ = ["blueprint_from_context"]
