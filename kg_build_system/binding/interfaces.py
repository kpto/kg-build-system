"""Internal interface of the graph-binding domain.

Another subpackage imports the frozen binding model, the validated factories,
the binding language and its part codec here. A graph author writes the names
re-exported by :mod:`kg_build_system.binding`; the compilation IR is
:mod:`kg_build_system.binding.ir`.
"""
from __future__ import annotations

from .factories import edge_binding, node_binding
from .ir import BindingIR, EdgeBindingIR, NodeBindingIR
from .language import (
    BindingLanguage, decode_binding, decode_binding_part, encode_binding,
    encode_binding_part,
)
from .models import (
    Binding, BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
    PropertyValues,
)

__all__ = [
    "Binding", "BindingIR", "BindingLanguage", "BindingOptions", "EdgeBinding",
    "EdgeBindingIR", "EdgeValues", "NodeBinding", "NodeBindingIR", "NodeValues",
    "PropertyValues", "decode_binding", "decode_binding_part", "edge_binding",
    "encode_binding", "encode_binding_part", "node_binding",
]
