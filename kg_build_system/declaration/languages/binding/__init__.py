"""Author-facing graph bindings.

A graph author writes :func:`node_binding` and :func:`edge_binding` and reads
the :class:`NodeBinding` and :class:`EdgeBinding` values they return. The
public surface lives in
:mod:`kg_build_system.declaration.languages.binding.public`; the internal
model, DTO and language live in the package's ``internal`` zone.
"""
from __future__ import annotations

from .public import (
    Binding,
    BindingMode,
    BindingOptions,
    EdgeBinding,
    EdgeValues,
    NodeBinding,
    NodeValues,
    PropertyValues,
    PythonRef,
    edge_binding,
    node_binding,
)

__all__ = [
    "Binding", "BindingMode", "BindingOptions", "EdgeBinding", "EdgeValues",
    "NodeBinding", "NodeValues", "PropertyValues", "PythonRef", "edge_binding",
    "node_binding",
]
