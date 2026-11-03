"""Framework-internal topology service interface.

Codec, source rendering, transcription, declaration accessors and the kernel
language adapter are resolved through this package.
"""
from __future__ import annotations

from .adapters import TopologyLanguage
from .codec import graph_from_document, graph_to_document
from .endpoints import make_endpoint
from .metadata import (
    component_kind,
    is_abstract_component,
    is_concrete_component,
    metadata_for,
    properties_for,
)
from .properties import make_property
from .source import render_graph_source
from .transcription import (
    collect_components,
    transcribe_graph_part,
    validate_graph_part,
)

__all__ = [
    "TopologyLanguage", "collect_components", "component_kind",
    "graph_from_document", "graph_to_document", "is_abstract_component",
    "is_concrete_component", "make_endpoint", "make_property", "metadata_for",
    "properties_for", "render_graph_source", "transcribe_graph_part",
    "validate_graph_part",
]
