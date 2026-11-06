"""Blueprint document codec.

The blueprint codec composes the layer codecs. It does not inspect a layer DTO
or duplicate its document shape; the graph, data and binding documents are
produced and consumed by the language that owns each DTO.
"""
from __future__ import annotations

from typing import Any, Mapping

from kg_build_system.distribution.languages.asset.service.internal.codec import assets_from_document, assets_to_document
from kg_build_system.distribution.languages.binding.service.internal.codec import binding_from_document, binding_to_document
from kg_build_system.distribution.languages.data.service.internal.codec import data_from_document, data_to_document
from kg_build_system.distribution.languages.graph.service.internal import (
    graph_declaration_from_document,
    graph_declaration_to_document,
)
from kg_build_system.distribution.languages.topology.service.internal.codec import graph_from_document, graph_to_document
from ...model.public import GraphBlueprint


def blueprint_to_document(blueprint: GraphBlueprint) -> dict[str, Any]:
    """Encode a blueprint into its canonical JSON-compatible document.

    The document has one member per layer codec: ``graph_declaration`` when the
    project has a graph declaration, then ``graph``, ``data``, ``assets`` and
    ``bindings``. The graph declaration member is omitted when absent.
    """
    document: dict[str, Any] = {}
    if blueprint.graph_declaration is not None:
        document["graph_declaration"] = graph_declaration_to_document(
            blueprint.graph_declaration
        )
    document["graph"] = graph_to_document(blueprint.graph)
    document["data"] = data_to_document(blueprint.data)
    document["assets"] = assets_to_document(blueprint.assets)
    document["bindings"] = [
        binding_to_document(binding) for binding in blueprint.bindings
    ]
    return document


def blueprint_from_document(value: Mapping[str, Any]) -> GraphBlueprint:
    """Decode a blueprint from the document produced by the blueprint codec.

    The layer codecs reconstruct their own DTOs; the blueprint only wraps them.
    A document without ``graph_declaration`` remains valid and decodes to
    ``None``.
    """
    graph = graph_from_document(value["graph"])
    data = data_from_document(value["data"])
    assets = assets_from_document(value.get("assets", ()))
    documents = value.get("bindings", value.get("binding", ()))
    bindings = tuple(binding_from_document(item) for item in documents)
    declaration_document = value.get("graph_declaration")
    graph_declaration = (
        None if declaration_document is None
        else graph_declaration_from_document(declaration_document)
    )
    return GraphBlueprint(
        graph=graph,
        data=data,
        assets=assets,
        bindings=bindings,
        graph_declaration=graph_declaration,
    )


__all__ = ["blueprint_from_document", "blueprint_to_document"]
