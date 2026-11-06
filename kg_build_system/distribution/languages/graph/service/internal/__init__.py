"""Framework-internal graph service interface.

Codec, source rendering and the kernel language adapter are resolved through
this package. The mechanisms live in ``service._private``; each name here is a
thin delegation.
"""
from __future__ import annotations

from .adapters import GraphLanguage
from .codec import (
    graph_declaration_from_document,
    graph_declaration_to_document,
)
from .source import render_graph_declaration_source

__all__ = [
    "GraphLanguage",
    "graph_declaration_from_document",
    "graph_declaration_to_document",
    "render_graph_declaration_source",
]
