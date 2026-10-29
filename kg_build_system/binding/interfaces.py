"""Framework-internal interface of the graph-binding domain.

Other subpackages import the binding model they compile, the binding IR codec
and the validated factories here. A graph author writes the factories and
values re-exported by :mod:`kg_build_system.binding`; the compilation IR is
:mod:`kg_build_system.binding.ir`.
"""
from __future__ import annotations

from .factories import edge_binding, node_binding
from .models import (
    Binding,
    BindingOptions,
    EdgeBinding,
    EdgeValues,
    NodeBinding,
    NodeValues,
)

__all__ = [
    "Binding",
    "BindingOptions",
    "EdgeBinding",
    "EdgeValues",
    "NodeBinding",
    "NodeValues",
    "edge_binding",
    "node_binding",
]
