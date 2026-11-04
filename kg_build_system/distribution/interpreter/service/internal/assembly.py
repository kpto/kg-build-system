"""Internal wrapper over the private blueprint assembly."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import DataPartDTO
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import GraphPartDTO
from ...model.public import BindingDTO, GraphBlueprint


def assemble_blueprint(
    graph: GraphPartDTO,
    data: DataPartDTO,
    bindings: Sequence[BindingDTO],
) -> GraphBlueprint:
    """Assemble the layer DTOs into one blueprint handle."""
    from .._private.assembly import assemble_blueprint as implementation

    return implementation(graph, data, bindings)


__all__ = ["assemble_blueprint"]
