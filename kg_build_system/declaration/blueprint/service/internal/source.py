"""Internal wrapper over the private blueprint source renderer."""
from __future__ import annotations

from typing import Any

from ...model.public import GraphBlueprint


def blueprint_to_source(blueprint: GraphBlueprint, context: Any) -> str:
    """Render a blueprint as authoring source."""
    from .._private.source import blueprint_to_source as implementation

    return implementation(blueprint, context)


__all__ = ["blueprint_to_source"]
