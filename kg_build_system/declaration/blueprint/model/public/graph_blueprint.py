"""The public graph blueprint handle.

A blueprint is the semantic model of one graph: its topology, its data
declarations, the bindings that populate it and the physical sources those
relations read. The layer DTOs are owned by their language packages; the
blueprint only references them.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.declaration.languages.binding.model.internal.dto.blueprint_dto import BindingDTO
from kg_build_system.declaration.languages.table.model.internal.dto.blueprint_dto import DataPartDTO, SourceDTO
from kg_build_system.declaration.languages.topology.model.internal.dto.blueprint_dto import GraphPartDTO


@dataclass(frozen=True, slots=True)
class GraphBlueprint:
    """One validated graph model assembled from the declaration layers.

    ``graph`` is the topology, ``data`` holds structs, relations and
    projections, ``bindings`` target graph components, and ``sources`` bind
    relations to physical locations. The value is frozen and carries no owner,
    service or Python authoring path.

    Example:
    ```python
    from kg_build_system.declaration.blueprint import create_blueprint

    blueprint = create_blueprint(namespace_path="graph_pipeline")
    nodes = blueprint.graph.nodes
    sources = blueprint.sources
    ```
    """

    graph: GraphPartDTO
    data: DataPartDTO
    bindings: tuple[BindingDTO, ...]
    sources: tuple[SourceDTO, ...]


__all__ = ["BindingDTO", "GraphBlueprint"]
