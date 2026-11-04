"""Core planner inputs and blueprint selection.

The artifact vocabulary itself lives in one distribution model module. This
service module keeps the design-time query over the blueprint and the one
helper that turns a relation name into an input opening.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.topology.model.internal.dto import (
    EdgeDTO,
    NodeDTO,
)
from kg_build_system.distribution.model.public.artifacts import CoreArtifactTypes
from kg_build_system.kernel import ArtifactPattern, Input

ComponentDTO = NodeDTO | EdgeDTO


def read_input(
    name: str,
    projection_relations: Mapping[str, str],
    row_source_relations: Mapping[str, str] | None = None,
) -> Input:
    """One opening a projection or binding takes: a relation its SQL reads."""
    if row_source_relations is not None and name in row_source_relations:
        return Input(
            type=ArtifactPattern(CoreArtifactTypes.row_source(name).key),
            opening_name=None,
            declared_name=f"row_source.{name}",
        )
    projection = name in projection_relations
    artifact_type = (
        CoreArtifactTypes.projection(name) if projection
        else CoreArtifactTypes.table(name)
    )
    return Input(
        type=ArtifactPattern(artifact_type.key),
        opening_name=None,
        declared_name=f"{'projection' if projection else 'table'}.{name}",
    )


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
    "component_kind",
    "graph_components",
    "graph_record_components",
    "read_input",
]
