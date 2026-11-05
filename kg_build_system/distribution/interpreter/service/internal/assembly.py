"""Internal wrapper over the private blueprint assembly."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.languages.asset.model.internal.dto import AssetPartDTO
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import DataPartDTO
from kg_build_system.distribution.languages.binding.model.internal.dto.blueprint_dto import BindingDTO
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import GraphPartDTO
from ...model.public import GraphBlueprint


def assemble_blueprint(
    graph: GraphPartDTO,
    data: DataPartDTO,
    assets: AssetPartDTO,
    bindings: Sequence[BindingDTO],
) -> GraphBlueprint:
    """Assemble the layer DTOs into one blueprint handle."""
    from .._private.assembly import assemble_blueprint as implementation

    return implementation(graph, data, assets, bindings)


__all__ = ["assemble_blueprint"]
