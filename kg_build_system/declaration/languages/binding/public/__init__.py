"""Author-facing binding factories, values and options.

Example:
    ```python
    from kg_build_system.declaration.languages.binding import node_binding

    binding = node_binding(
        target=UnitNode,
        build_key=UnitTable.unit_ref,
        properties=UnitNode(name=UnitTable.unit_name),
    )
    ```
"""
from __future__ import annotations

from .builders import edge_binding, node_binding
from .model import (
    Binding,
    BindingMode,
    BindingOptions,
    EdgeBinding,
    EdgeValues,
    NodeBinding,
    NodeValues,
    PropertyValues,
    PythonRef,
)

__all__ = [
    "Binding", "BindingMode", "BindingOptions", "EdgeBinding", "EdgeValues",
    "NodeBinding", "NodeValues", "PropertyValues", "PythonRef", "edge_binding",
    "node_binding",
]
