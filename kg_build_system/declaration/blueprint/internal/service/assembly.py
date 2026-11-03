"""Assemble the layer DTOs into one public blueprint handle.

Assembly is a structural operation: the graph DTOs already name nodes, edges,
endpoints and parents, so no authoring module path or declaration expression is
introduced here.
"""
from __future__ import annotations

from collections.abc import Sequence

from ....languages.table.internal.dto.blueprint_dto import DataPartDTO
from ....languages.topology.internal.dto.blueprint_dto import GraphPartDTO
from ...public.dto.graph_blueprint import BindingDTO, GraphBlueprint


def assemble_blueprint(
    graph: GraphPartDTO,
    data: DataPartDTO,
    bindings: Sequence[BindingDTO],
) -> GraphBlueprint:
    """Assemble the layer DTOs into one blueprint handle.

    Physical sources belong to the table language DTO and are exposed as the
    blueprint's ``sources`` view. No authoring module path is introduced.

    Example:
    ```python
    from kg_build_system.declaration.blueprint.internal import assemble_blueprint

    blueprint = assemble_blueprint(graph, data, bindings)
    ```
    """
    return GraphBlueprint(
        graph=graph,
        data=data,
        bindings=tuple(bindings),
        sources=tuple(getattr(data, "sources", ())),
    )


__all__ = ["assemble_blueprint"]
