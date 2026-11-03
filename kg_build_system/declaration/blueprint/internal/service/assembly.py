"""Internal wrapper over the private blueprint assembly."""
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
    """Assemble the layer DTOs into one blueprint handle."""
    from ..._private.assembly import assemble_blueprint as implementation

    return implementation(graph, data, bindings)


__all__ = ["assemble_blueprint"]
