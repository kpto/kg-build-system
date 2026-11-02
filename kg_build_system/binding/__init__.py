"""Author-facing graph bindings.

A graph author writes :func:`node_binding` and :func:`edge_binding` and reads
the :class:`NodeBinding` and :class:`EdgeBinding` values they return. The
framework-internal model, the language and the codec are
:mod:`kg_build_system.binding.interfaces`; the compilation IR is
:mod:`kg_build_system.binding.ir`.
"""
from __future__ import annotations

from .factories import edge_binding, node_binding
from .models import (
    Binding, BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
)

__all__ = [
    "Binding", "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
    "NodeValues", "edge_binding", "node_binding",
]
