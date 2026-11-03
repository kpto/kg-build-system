"""Framework-internal interface of the topology language.

The interface is the DTO, the introspected declaration metadata, the kernel
language adapter and source generation. Authoring names remain in
:mod:`kg_build_system.declaration.languages.topology.public`.
"""
from __future__ import annotations

from .adapters import TopologyLanguage
from .dto import (
    EdgeDTO,
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
    graph_from_document,
    graph_to_document,
)
from .model import (
    ComponentMetadata,
    PropertyDeclaration,
    component_kind,
    is_abstract_component,
    is_concrete_component,
    metadata_for,
    properties_for,
)
from .service import render_graph_source

__all__ = [
    "ComponentMetadata", "EdgeDTO", "GraphPartDTO", "NodeDTO",
    "PropertyDTO", "PropertyDeclaration", "TopologyLanguage",
    "component_kind", "graph_from_document", "graph_to_document",
    "is_abstract_component", "is_concrete_component", "metadata_for",
    "properties_for", "render_graph_source",
]
