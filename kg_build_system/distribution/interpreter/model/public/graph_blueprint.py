"""The public graph blueprint handle.

A blueprint is the semantic model of one graph: its topology, its data
declarations, the logical assets its relations are read from and the bindings
that populate it. The layer DTOs are owned by their language packages; the
blueprint only references them.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.asset.model.internal.dto import (
    AssetPartDTO,
)
from kg_build_system.distribution.languages.binding.model.internal.dto.blueprint_dto import BindingDTO
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import DataPartDTO
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import GraphPartDTO


@dataclass(frozen=True, slots=True)
class GraphBlueprint:
    """One validated graph model assembled from the declaration layers.

    ``graph`` is the topology, ``data`` holds structs, relations and
    projections, ``assets`` holds the logical source-data units relations name,
    and ``bindings`` target graph components. The value is frozen and carries no
    owner, service or Python authoring path.

    Example:
    ```python
    from kg_build_system.distribution.interpreter import create_blueprint

    blueprint = create_blueprint(namespace_path="graph_pipeline")
    nodes = blueprint.graph.nodes
    assets = blueprint.assets.assets
    ```
    """

    graph: GraphPartDTO
    data: DataPartDTO
    assets: AssetPartDTO
    bindings: tuple[BindingDTO, ...]


__all__ = ["BindingDTO", "GraphBlueprint"]
