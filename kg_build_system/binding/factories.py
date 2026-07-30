"""Binding factory functions."""
from typing import Any
from .models import EdgeBinding, NodeBinding
from .provide import normalise

def node_binding(*, target: type, build_key: Any, properties: Any) -> NodeBinding:
    return NodeBinding(target, normalise(build_key), properties)

def edge_binding(*, target: type, build_key: Any, source_build_key: Any, target_build_key: Any, properties: Any) -> EdgeBinding:
    return EdgeBinding(target, normalise(build_key), normalise(source_build_key), normalise(target_build_key), properties)
