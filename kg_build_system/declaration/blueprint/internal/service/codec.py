"""Internal wrapper over the private blueprint document codec."""
from __future__ import annotations

from typing import Any, Mapping

from ...public.dto.graph_blueprint import GraphBlueprint


def blueprint_to_document(blueprint: GraphBlueprint) -> dict[str, Any]:
    """Encode a blueprint into its canonical JSON-compatible document."""
    from ..._private.codec import blueprint_to_document as implementation

    return implementation(blueprint)


def blueprint_from_document(value: Mapping[str, Any]) -> GraphBlueprint:
    """Decode a blueprint from the document produced by the blueprint codec."""
    from ..._private.codec import blueprint_from_document as implementation

    return implementation(value)


__all__ = ["blueprint_from_document", "blueprint_to_document"]
