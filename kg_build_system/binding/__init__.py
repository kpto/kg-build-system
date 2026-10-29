"""Author-facing graph bindings.

A graph author writes ``node_binding`` and ``edge_binding`` here and reads the
``NodeBinding``/``EdgeBinding`` values they return. The framework-internal
binding model and codec are :mod:`kg_build_system.binding.interfaces`; the
compilation IR is :mod:`kg_build_system.binding.ir`.
"""
from __future__ import annotations

from .factories import edge_binding, node_binding
from .models import (
    BindingOptions,
    EdgeBinding,
    EdgeValues,
    NodeBinding,
    NodeValues,
)

__all__ = [
    "BindingOptions",
    "EdgeBinding",
    "EdgeValues",
    "NodeBinding",
    "NodeValues",
    "edge_binding",
    "node_binding",
]
