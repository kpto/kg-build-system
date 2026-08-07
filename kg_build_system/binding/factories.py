"""Binding factory functions."""
from typing import Any
from ..topology.models import Edge, GraphValue, Node
from .models import BindingOptions, EdgeBinding, ExpressionBinding, NodeBinding


def _require_binding[T: GraphValue](value: ExpressionBinding[T], *, argument: str) -> ExpressionBinding[T]:
    if not isinstance(value, ExpressionBinding):
        raise TypeError(f"{argument} must be assigned with bind(...)")
    return value


def _require_properties[C: Node | Edge[Any, Any]](value: C, *, target: type[C]) -> C:
    if not isinstance(value, target):
        raise TypeError(f"properties must be an instance of {target.__name__}")
    return value


def node_binding[N: Node](*, target: type[N], build_key: ExpressionBinding[str], properties: N, debug_name: str | None = None, options: BindingOptions = BindingOptions()) -> NodeBinding[N]:
    return NodeBinding(debug_name, target, _require_binding(build_key, argument="build_key"), _require_properties(properties, target=target), tuple(options.annotations))


def edge_binding[E: Edge[Any, Any]](*, target: type[E], build_key: ExpressionBinding[str], source_build_key: ExpressionBinding[str], target_build_key: ExpressionBinding[str], properties: E, debug_name: str | None = None, options: BindingOptions = BindingOptions()) -> EdgeBinding[E]:
    return EdgeBinding(
        debug_name,
        target,
        _require_binding(build_key, argument="build_key"),
        _require_binding(source_build_key, argument="source_build_key"),
        _require_binding(target_build_key, argument="target_build_key"),
        _require_properties(properties, target=target),
        tuple(options.annotations),
    )
