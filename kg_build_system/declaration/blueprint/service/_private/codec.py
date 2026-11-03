"""Blueprint document codec.

The blueprint codec composes the layer codecs. It does not inspect a layer DTO
or duplicate its document shape; the graph, data and binding documents are
produced and consumed by the language that owns each DTO.
"""
from __future__ import annotations

from typing import Any, Mapping

from kg_build_system.declaration.languages.binding.service.internal.codec import binding_from_document, binding_to_document
from kg_build_system.declaration.languages.table.service.internal.codec import data_from_document, data_to_document
from kg_build_system.declaration.languages.topology.service.internal.codec import graph_from_document, graph_to_document
from ...model.public import GraphBlueprint


def blueprint_to_document(blueprint: GraphBlueprint) -> dict[str, Any]:
    """Encode a blueprint into its canonical JSON-compatible document.

    The document has one member per layer codec: ``graph``, ``data`` and
    ``bindings``. Physical sources are encoded by the table DTO.
    """
    return {
        "graph": graph_to_document(blueprint.graph),
        "data": data_to_document(blueprint.data),
        "bindings": [
            binding_to_document(binding) for binding in blueprint.bindings
        ],
    }


def blueprint_from_document(value: Mapping[str, Any]) -> GraphBlueprint:
    """Decode a blueprint from the document produced by the blueprint codec.

    The layer codecs reconstruct their own DTOs; the blueprint only wraps them.
    """
    graph = graph_from_document(value["graph"])
    data = data_from_document(value["data"])
    documents = value.get("bindings", value.get("binding", ()))
    bindings = tuple(binding_from_document(item) for item in documents)
    return GraphBlueprint(
        graph=graph,
        data=data,
        bindings=bindings,
        sources=tuple(getattr(data, "sources", ())),
    )


__all__ = ["blueprint_from_document", "blueprint_to_document"]
