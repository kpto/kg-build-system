"""Validated graph-binding factories."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, overload

from ..expressions import ValueExpression, ValueInput, as_expression
from ..table.models import RowSource
from ..table.rows import DerivedRowSource, RelationRowSource
from ..topology.models import Edge, Endpoint, Node, NonNullableGraphValue, _NodeSideBase
from ..types import NullableType, Shape, require_non_nullable, require_scalar
from .models import BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues


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


def _require_row_source(value: Any) -> None:
    if isinstance(value, type):
        if not issubclass(value, RowSource):
            raise TypeError("rows must be a RowSource, a RowSource class, or a DerivedRowSource")
        return
    if not isinstance(value, (DerivedRowSource, RelationRowSource)):
        raise TypeError("rows must be a RowSource, a RowSource class, or a DerivedRowSource")


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


@overload
def node_binding[N: Node, S: Shape](
    *, target: type[N], rows: type[S] | DerivedRowSource[S],
    bind: Callable[[type[S]], NodeValues[N, Any]],
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]: ...
@overload
def node_binding[N: Node, Key: NonNullableGraphValue](
    *, target: type[N], build_key: ValueInput[Key], properties: N,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]: ...
def node_binding[N: Node](
    *, target: type[N], build_key: ValueInput[Any] | None = None,
    properties: Any = None, rows: Any = None, bind: Any = None,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]:
    _require_concrete_component(target, "node")
    if rows is not None or bind is not None:
        if build_key is not None or properties is not None:
            raise TypeError("node_binding takes either build_key/properties or rows/bind")
        if rows is None or bind is None:
            raise TypeError("rows and bind must be supplied together")
        shape = rows.shape if isinstance(rows, (DerivedRowSource, RelationRowSource)) else rows
        _require_row_source(rows)
        values = bind(shape)
        if not isinstance(values, NodeValues):
            raise TypeError("node_binding bind must return NodeValues")
        build_key, properties = values.build_key, values.properties
    elif build_key is None or properties is None:
        raise TypeError("node_binding requires build_key and properties, or rows and bind")
    return NodeBinding(
        debug_name, target, _require_key(build_key, argument="build_key"),
        _require_properties(properties, target=target), tuple(options.annotations),
        rows,
    )


@overload
def edge_binding[E: Edge[Any, Any], S: Shape](
    *, target: type[E], rows: type[S] | DerivedRowSource[S],
    bind: Callable[[type[S]], EdgeValues[E, Any, Any, Any]],
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
    source_node: Endpoint[Any] | None = None,
    target_node: Endpoint[Any] | None = None,
) -> EdgeBinding[E]: ...
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
    *, target: type[Edge[Any, Any]], build_key: ValueInput[Any] | None = None,
    source_build_key: ValueInput[Any] | None = None,
    target_build_key: ValueInput[Any] | None = None, properties: Any = None,
    rows: Any = None, bind: Any = None,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
    source_node: Endpoint[Any] | None = None,
    target_node: Endpoint[Any] | None = None,
) -> EdgeBinding[Any]:
    _require_concrete_component(target, "edge")
    if rows is not None or bind is not None:
        if any(value is not None for value in (
            build_key, source_build_key, target_build_key, properties,
        )):
            raise TypeError("edge_binding takes either key/properties or rows/bind")
        if rows is None or bind is None:
            raise TypeError("rows and bind must be supplied together")
        shape = rows.shape if isinstance(rows, (DerivedRowSource, RelationRowSource)) else rows
        _require_row_source(rows)
        values = bind(shape)
        if not isinstance(values, EdgeValues):
            raise TypeError("edge_binding bind must return EdgeValues")
        build_key, properties = values.build_key, values.properties
        source_build_key, target_build_key = (
            values.source_build_key, values.target_build_key,
        )
    elif any(value is None for value in (
        build_key, source_build_key, target_build_key, properties,
    )):
        raise TypeError(
            "edge_binding requires keys and properties, or rows and bind"
        )
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
        rows,
    )


__all__ = ["edge_binding", "node_binding"]
