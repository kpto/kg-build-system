"""Single-label annotation types."""
from __future__ import annotations

from dataclasses import dataclass

from .models import Annotation


@dataclass(frozen=True)
class NodeLabel(Annotation):
    namespace = "kg_build_system.topology"
    annotation_id = "node_label"

    label: str

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("node labels require a non-empty label")


@dataclass(frozen=True)
class EdgeLabel(Annotation):
    namespace = "kg_build_system.topology"
    annotation_id = "edge_label"

    label: str

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("edge labels require a non-empty label")


__all__ = ["EdgeLabel", "NodeLabel"]
