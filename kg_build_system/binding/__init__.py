"""Author-facing graph bindings.

A graph author writes :func:`node_binding` and :func:`edge_binding` and reads
the :class:`NodeBinding` and :class:`EdgeBinding` values they return. The public
surface lives in :mod:`kg_build_system.binding.public`; the internal model and
language live in :mod:`kg_build_system.binding.internal`.
"""
from __future__ import annotations

from .public import (
    Binding, BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
    edge_binding, node_binding,
)

__all__ = [
    "Binding", "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
    "NodeValues", "edge_binding", "node_binding",
]
