"""Blueprint selection for the deduplication planner."""
from __future__ import annotations

from typing import Literal

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.topology.model.internal.dto import (
    EdgeDTO,
    NodeDTO,
)

ComponentDTO = NodeDTO | EdgeDTO


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


__all__ = ["ComponentDTO", "component_kind", "graph_record_components"]
