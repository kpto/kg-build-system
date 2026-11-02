"""Binding values and options returned to a graph author.

``NodeBinding`` and ``EdgeBinding`` are the frozen results of the binding
factories; ``NodeValues`` and ``EdgeValues`` are the row-derived values a
``bind`` callable returns; ``BindingOptions`` attaches portable annotations.

Example:
    ```python
    from kg_build_system import BindingOptions, NodeBinding, node_binding

    options = BindingOptions()
    binding: NodeBinding[UnitNode] = node_binding(
        target=UnitNode,
        build_key=UnitTable.unit_ref,
        properties=UnitNode(name=UnitTable.unit_name),
        options=options,
    )
    ```
"""
from __future__ import annotations

from ..internal.models import (
    Binding, BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
    PropertyValues,
)

__all__ = [
    "Binding", "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
    "NodeValues", "PropertyValues",
]
