"""Validated graph-binding factories."""
from __future__ import annotations

from typing import Any, overload

from ..expressions import ValueExpression, ValueInput, as_expression
from ..topology.models import Edge, Endpoint, Node, NonNullableGraphValue, _NodeSideBase
from ..types import NullableType, require_non_nullable, require_scalar
from .models import BindingOptions, EdgeBinding, NodeBinding


def _require_key(value: object, *, argument: str) -> ValueExpression[Any]:
    try:
        expression = as_expression(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(f"{argument} must be a value selection or expression") from error
    require_non_nullable(require_scalar(expression.logical_type, context=argument), context=argument)
    return expression


def _compatible(expected: object, actual: object) -> bool:
    return expected == actual or (
        isinstance(expected, NullableType) and expected.value == actual
    )


def _require_properties[C: Node | Edge[Any, Any]](value: C, *, target: type[C]) -> C:
    if not isinstance(value, target):
        raise TypeError(f"properties must be an instance of {target.__name__}")
    for attribute, declaration in target._properties.items():
        try:
            expression = as_expression(getattr(value, attribute))
        except TypeError as error:
            raise TypeError(
                f"{target.__name__}.{attribute} must be assigned a value selection or expression"
            ) from error
        expected = declaration.logical_type
        assert expected is not None
        if not _compatible(expected, expression.logical_type):
            raise TypeError(
                f"{target.__name__}.{attribute} expects {expected!r}, "
                f"but the expression resolves to {expression.logical_type!r}"
            )
        setattr(value, attribute, expression)
    return value


def _require_concrete_component(target: Any, kind: str) -> None:
    if (
        not isinstance(target, type)
        or vars(target).get("_component_declaration_kind") != kind
        or vars(target).get("_component_abstract", False)
    ):
        name = getattr(target, "__name__", repr(target))
        raise TypeError(f"target must be a concrete {kind} component, not {name}")


def _resolve_endpoint(
    token: Any, *, declared: Any, side: str,
) -> type[Node] | None:
    """Each endpoint token is required exactly when its declared endpoint is abstract."""
    declared_is_abstract = bool(
        isinstance(declared, type) and vars(declared).get("_component_abstract", False)
    )
    if token is None:
        if declared_is_abstract:
            raise TypeError(
                f"{side}_node must name the declared endpoint category "
                f"{declared.__name__}: pass endpoint(...) for that side"
            )
        return None
    if not isinstance(token, Endpoint):
        raise TypeError(
            f"{side}_node must be an endpoint(...) token, not the raw value {token!r}"
        )
    selected = token.target
    if (
        not isinstance(selected, type)
        or vars(selected).get("_component_declaration_kind") != "node"
        or vars(selected).get("_component_abstract", False)
    ):
        name = getattr(selected, "__name__", repr(selected))
        raise TypeError(f"{side}_node must name a concrete node component, not {name}")
    if not issubclass(selected, declared):
        raise TypeError(
            f"{side}_node {selected.__name__} must equal or descend from the "
            f"declared endpoint category {declared.__name__}"
        )
    return selected


def node_binding[N: Node, Key: NonNullableGraphValue](
    *, target: type[N], build_key: ValueInput[Key], properties: N,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]:
    _require_concrete_component(target, "node")
    return NodeBinding(
        debug_name, target, _require_key(build_key, argument="build_key"),
        _require_properties(properties, target=target), tuple(options.annotations),
    )


@overload
def edge_binding[
    E: Edge[Any, Any], S: Node, D: Node, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[S, D]], build_key: ValueInput[Key],
    source_build_key: ValueInput[SourceKey],
    target_build_key: ValueInput[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...
@overload
def edge_binding[
    E: Edge[Any, Any], S: Node, DC: _NodeSideBase, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[S, DC]], target_node: Endpoint[DC],
    build_key: ValueInput[Key],
    source_build_key: ValueInput[SourceKey],
    target_build_key: ValueInput[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...
@overload
def edge_binding[
    E: Edge[Any, Any], SC: _NodeSideBase, D: Node, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[SC, D]], source_node: Endpoint[SC],
    build_key: ValueInput[Key],
    source_build_key: ValueInput[SourceKey],
    target_build_key: ValueInput[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...
@overload
def edge_binding[
    E: Edge[Any, Any], SC: _NodeSideBase, DC: _NodeSideBase,
    Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[SC, DC]], source_node: Endpoint[SC],
    target_node: Endpoint[DC], build_key: ValueInput[Key],
    source_build_key: ValueInput[SourceKey],
    target_build_key: ValueInput[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...
def edge_binding(
    *, target: type[Edge[Any, Any]], build_key: ValueInput[Any],
    source_build_key: ValueInput[Any],
    target_build_key: ValueInput[Any], properties: Any,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
    source_node: Endpoint[Any] | None = None,
    target_node: Endpoint[Any] | None = None,
) -> EdgeBinding[Any]:
    _require_concrete_component(target, "edge")
    declared_source = target._metadata["source"]
    declared_target = target._metadata["target"]
    return EdgeBinding(
        debug_name, target,
        _require_key(build_key, argument="build_key"),
        _require_key(source_build_key, argument="source_build_key"),
        _require_key(target_build_key, argument="target_build_key"),
        _require_properties(properties, target=target), tuple(options.annotations),
        _resolve_endpoint(source_node, declared=declared_source, side="source"),
        _resolve_endpoint(target_node, declared=declared_target, side="target"),
    )


__all__ = ["edge_binding", "node_binding"]
