"""Portable single-label annotations.

Example:
    ```python
    from kg_build_system.declaration.foundations.annotations import (
        EdgeLabel, NodeLabel,
    )

    NodeLabel("Sensor")
    EdgeLabel("MEASURES")
    ```
"""
from __future__ import annotations

from dataclasses import dataclass

from .base import Annotation


@dataclass(frozen=True)
class NodeLabel(Annotation):
    """A portable semantic label for a node component.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations import NodeLabel

        NodeLabel("Sensor")
        ```
    """

    namespace = "kg_build_system.topology"
    annotation_id = "node_label"

    label: str

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("node labels require a non-empty label")


@dataclass(frozen=True)
class EdgeLabel(Annotation):
    """A portable semantic label for an edge component.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations import EdgeLabel

        EdgeLabel("MEASURES")
        ```
    """

    namespace = "kg_build_system.topology"
    annotation_id = "edge_label"

    label: str

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("edge labels require a non-empty label")


__all__ = ["EdgeLabel", "NodeLabel"]
