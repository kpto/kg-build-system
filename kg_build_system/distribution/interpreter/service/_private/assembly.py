"""Assemble the layer DTOs into one public blueprint handle.

Assembly is a structural operation: the graph DTOs already name nodes, edges,
endpoints and parents, and the data relations already name their assets, so no
authoring module path or declaration expression is introduced here.
"""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.languages.asset.model.internal.dto import AssetPartDTO
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import DataPartDTO
from kg_build_system.distribution.languages.binding.model.internal.dto.blueprint_dto import BindingDTO
from kg_build_system.distribution.languages.expressions.model.internal.dto.operation_dto import ExpressionsPartDTO
from kg_build_system.distribution.languages.graph.model.internal.dto import GraphDeclarationDTO
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import GraphPartDTO
from ...model.public import GraphBlueprint


def assemble_blueprint(
    graph: GraphPartDTO,
    data: DataPartDTO,
    assets: AssetPartDTO,
    bindings: Sequence[BindingDTO],
    graph_declaration: GraphDeclarationDTO | None = None,
    operations: ExpressionsPartDTO | None = None,
) -> GraphBlueprint:
    """Assemble the layer DTOs into one blueprint handle.

    ``graph_declaration`` is passed through unchanged; the blueprint does not
    derive or validate it. ``operations`` defaults to the empty expressions
    part.
    """
    return GraphBlueprint(
        graph=graph,
        data=data,
        assets=assets,
        bindings=tuple(bindings),
        graph_declaration=graph_declaration,
        operations=ExpressionsPartDTO() if operations is None else operations,
    )


__all__ = ["assemble_blueprint"]
