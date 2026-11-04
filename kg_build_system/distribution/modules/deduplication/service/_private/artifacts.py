"""Artifact vocabulary shared with the core planner's graph records."""
from __future__ import annotations

from typing import Literal

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.topology.model.internal.dto import (
    EdgeDTO,
    NodeDTO,
)
from kg_build_system.kernel import ArtifactType

ComponentDTO = NodeDTO | EdgeDTO


class CoreArtifactTypes:
    """The graph-record artifact types a planner consumes and produces."""

    NAMESPACE = "core"

    @classmethod
    def graph_records(
        cls, kind: Literal["node", "edge"], component: str,
    ) -> ArtifactType:
        return ArtifactType(cls.NAMESPACE, f"graph.{kind}.{component}")


def component_kind(component: ComponentDTO) -> Literal["node", "edge"]:
    return "node" if isinstance(component, NodeDTO) else "edge"


def graph_record_components(
    blueprint: GraphBlueprint,
) -> tuple[ComponentDTO, ...]:
    bound = {binding.component for binding in blueprint.bindings}
    return tuple(
        component
        for component in (*blueprint.graph.nodes, *blueprint.graph.edges)
        if component.name in bound
    )


__all__ = [
    "ComponentDTO",
    "CoreArtifactTypes",
    "component_kind",
    "graph_record_components",
]
