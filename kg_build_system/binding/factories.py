"""Binding factory functions."""
from typing import Any
from .models import EdgeBinding, NodeBinding
from .expression_api import _to_expression

def node_binding(*, target: type, build_key: Any, properties: Any) -> NodeBinding:
    return NodeBinding(target, _to_expression(build_key), properties)

def edge_binding(*, target: type, build_key: Any, source_build_key: Any, target_build_key: Any, properties: Any) -> EdgeBinding:
    return EdgeBinding(target, _to_expression(build_key), _to_expression(source_build_key), _to_expression(target_build_key), properties)
