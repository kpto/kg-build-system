"""The artifact vocabulary the core planner produces and other planners read.

The names are the distribution's graph artifact vocabulary. Values are kernel
``ArtifactType`` objects so a planner can declare its ports without importing a
workflow plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.topology.model.internal.dto import (
    EdgeDTO,
    NodeDTO,
)
from kg_build_system.kernel import ArtifactType


ComponentDTO = NodeDTO | EdgeDTO


@dataclass(frozen=True, slots=True)
class GraphRecordArtifact:
    """The kind and component name encoded by one graph-record artifact type."""

    kind: Literal["node", "edge"]
    component: str


class CoreArtifactTypes:
    """Stable artifact types produced and consumed by graph workflow planners."""

    NAMESPACE = "core"

    @classmethod
    def graph_records(
        cls, kind: Literal["node", "edge"], component: str,
    ) -> ArtifactType:
        return ArtifactType(cls.NAMESPACE, f"graph.{kind}.{component}")

    @classmethod
    def binding(cls, identity: str) -> ArtifactType:
        return ArtifactType(cls.NAMESPACE, f"binding.{identity}")

    @classmethod
    def table(cls, name: str) -> ArtifactType:
        return ArtifactType(cls.NAMESPACE, f"data.table.{name}")

    @classmethod
    def projection(cls, name: str) -> ArtifactType:
        return ArtifactType(cls.NAMESPACE, f"data.projection.{name}")

    @classmethod
    def row_source(cls, key: str) -> ArtifactType:
        return ArtifactType(cls.NAMESPACE, f"data.row_source.{key}")

    @classmethod
    def graph_record_identity(
        cls, artifact_type: ArtifactType,
    ) -> GraphRecordArtifact | None:
        if artifact_type.namespace != cls.NAMESPACE:
            return None
        parts = artifact_type.name.split(".", 2)
        if (
            len(parts) != 3
            or parts[0] != "graph"
            or parts[1] not in {"node", "edge"}
            or not parts[2]
        ):
            return None
        return GraphRecordArtifact(
            kind=cast(Literal["node", "edge"], parts[1]),
            component=parts[2],
        )

    @classmethod
    def is_graph_records(cls, artifact_type: ArtifactType) -> bool:
        return cls.graph_record_identity(artifact_type) is not None


def component_kind(component: ComponentDTO) -> Literal["node", "edge"]:
    """The record kind of one selected component DTO."""
    return "node" if isinstance(component, NodeDTO) else "edge"


def graph_components(blueprint: GraphBlueprint) -> tuple[ComponentDTO, ...]:
    """Every node and edge in the graph, in graph order."""
    return (*blueprint.graph.nodes, *blueprint.graph.edges)


def graph_record_components(
    blueprint: GraphBlueprint,
) -> tuple[ComponentDTO, ...]:
    """Components that actually produce graph records.

    A component produces records only when at least one binding targets it.
    Abstract categories carry topology meaning and the parent chain, and are
    never binding targets, so they produce no aggregation step.
    """
    bound = {binding.component for binding in blueprint.bindings}
    return tuple(
        component for component in graph_components(blueprint)
        if component.name in bound
    )


__all__ = [
    "ComponentDTO",
    "CoreArtifactTypes",
    "GraphRecordArtifact",
    "component_kind",
    "graph_components",
    "graph_record_components",
]
