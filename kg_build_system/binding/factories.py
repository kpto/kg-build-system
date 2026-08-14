"""Validated graph-binding factories."""
from __future__ import annotations

from typing import Any

from ..expressions import AuthoringValueExpression, ValueExpression
from ..topology.models import Edge, Node, NonNullableGraphValue
from ..types import NullableType, require_non_nullable, require_scalar
from .models import BindingOptions, EdgeBinding, NodeBinding


def _require_key(value: object, *, argument: str) -> ValueExpression[Any]:
    if not isinstance(value, ValueExpression):
        raise TypeError(f"{argument} must be a value expression")
    require_non_nullable(require_scalar(value.logical_type, context=argument), context=argument)
    return value


def _compatible(expected: object, actual: object) -> bool:
    return expected == actual or (
        isinstance(expected, NullableType) and expected.value == actual
    )


def _require_properties[C: Node | Edge[Any, Any]](value: C, *, target: type[C]) -> C:
    if not isinstance(value, target):
        raise TypeError(f"properties must be an instance of {target.__name__}")
    for attribute, declaration in target._properties.items():
        expression = getattr(value, attribute)
        if not isinstance(expression, ValueExpression):
            raise TypeError(f"{target.__name__}.{attribute} must be assigned a value expression")
        expected = declaration.logical_type
        assert expected is not None
        if not _compatible(expected, expression.logical_type):
            raise TypeError(
                f"{target.__name__}.{attribute} expects {expected!r}, "
                f"but the expression resolves to {expression.logical_type!r}"
            )
    return value


def node_binding[N: Node, Key: NonNullableGraphValue](
    *, target: type[N], build_key: AuthoringValueExpression[Key], properties: N,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]:
    return NodeBinding(
        debug_name, target, _require_key(build_key, argument="build_key"),
        _require_properties(properties, target=target), tuple(options.annotations),
    )


def edge_binding[
    E: Edge[Any, Any], Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[E], build_key: AuthoringValueExpression[Key],
    source_build_key: AuthoringValueExpression[SourceKey],
    target_build_key: AuthoringValueExpression[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]:
    return EdgeBinding(
        debug_name, target,
        _require_key(build_key, argument="build_key"),
        _require_key(source_build_key, argument="source_build_key"),
        _require_key(target_build_key, argument="target_build_key"),
        _require_properties(properties, target=target), tuple(options.annotations),
    )


__all__ = ["edge_binding", "node_binding"]
