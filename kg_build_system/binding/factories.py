"""Binding factory functions."""
from typing import Any
from .models import EdgeBinding, NodeBinding
from .provide import normalise

def _normalise_properties(properties: Any) -> Any:
    """Apply the `ProvideInput` shortcut at the graph-binding boundary."""
    properties._values = {name: normalise(value) for name, value in properties._values.items()}
    return properties

def node_binding(*, target: type, build_key: Any, properties: Any) -> NodeBinding:
    return NodeBinding(target, normalise(build_key), _normalise_properties(properties))

def edge_binding(*, target: type, build_key: Any, source_build_key: Any, target_build_key: Any, properties: Any) -> EdgeBinding:
    return EdgeBinding(target, normalise(build_key), normalise(source_build_key), normalise(target_build_key), _normalise_properties(properties))
