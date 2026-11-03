"""The annotation's part of the graph blueprint."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import JsonValue


@dataclass(frozen=True, slots=True)
class AnnotationDTO:
    """One portable annotation carried by the blueprint.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations.service.internal import (
            AnnotationDTO,
        )

        AnnotationDTO("kg_build_system.topology", "node_label", {"label": "Sensor"})
        ```
    """

    namespace: str
    id: str
    arguments: JsonValue

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("annotation namespaces must be non-empty")
        if not self.id:
            raise ValueError("annotation ids must be non-empty")


__all__ = ["AnnotationDTO"]
