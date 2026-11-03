"""Compatibility re-export of the binding factories.

The factories are defined in
:mod:`kg_build_system.declaration.languages.binding.public.model.builders`.
"""
from __future__ import annotations

from .model.builders import edge_binding, node_binding

__all__ = ["edge_binding", "node_binding"]
