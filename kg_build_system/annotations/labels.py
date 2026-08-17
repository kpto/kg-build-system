"""Target-neutral labels for graph components."""
from __future__ import annotations

from dataclasses import dataclass

from .models import Annotation


GRAPH_ANNOTATION_NAMESPACE = "kg_build_system.topology"


def _validate_label(value: str, *, kind: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{kind} labels must be strings")
    if not value.strip():
        raise ValueError(f"{kind} labels must be non-empty")


@dataclass(frozen=True)
class NodeLabel(Annotation):
    """The single semantic label assigned to a node component."""

    namespace = GRAPH_ANNOTATION_NAMESPACE
    annotation_id = "node_label"

    label: str

    def __post_init__(self) -> None:
        _validate_label(self.label, kind="node")


@dataclass(frozen=True)
class EdgeLabel(Annotation):
    """The single semantic label assigned to an edge component."""

    namespace = GRAPH_ANNOTATION_NAMESPACE
    annotation_id = "edge_label"

    label: str

    def __post_init__(self) -> None:
        _validate_label(self.label, kind="edge")


__all__ = ["EdgeLabel", "GRAPH_ANNOTATION_NAMESPACE", "NodeLabel"]
