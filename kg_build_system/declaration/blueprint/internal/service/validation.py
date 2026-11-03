"""Internal wrapper over the private blueprint validation."""
from __future__ import annotations

from ...public.dto.graph_blueprint import GraphBlueprint


def validate_blueprint(blueprint: GraphBlueprint) -> None:
    """Reject a blueprint with colliding names or dangling references."""
    from ..._private.validation import validate_blueprint as implementation

    return implementation(blueprint)


__all__ = ["validate_blueprint"]
