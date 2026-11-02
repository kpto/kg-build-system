"""Validated graph-binding factories.

The factories are the only authoring boundary: they check the target, normalize
keys and property values, resolve endpoint tokens and convert a declaration
class passed as ``rows=`` into its row-source value. The resulting binding is
frozen data; the caller's property object is never mutated.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, overload

from ..expressions.interfaces import ValueExpression, ValueInput, as_expression
from ..table.interfaces import (
    DerivedRowSource, RelationRowSource, as_row_source, shape_context,
)
from ..topology.interfaces import (
    Edge, Endpoint, Node, NodeSideBase, NonNullableGraphValue,
    component_kind, is_abstract_component, properties_for,
)
from ..types.interfaces import (
    NullableType, Shape, require_non_nullable, require_scalar,
)
from .models import (
    BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
    PropertyValues,
)


def _require_key(value: object, *, argument: str) -> ValueExpression[Any]:
    try:
        expression = as_expression(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(
            f"{argument} must be a value selection or expression"
        ) from error
    require_non_nullable(
        require_scalar(expression.logical_type, context=argument),
        context=argument,
    )
    return expression


def _compatible(expected: object, actual: object) -> bool:
    """Compare a property's declared type with the supplied expression type.

    A non-null expression satisfies a nullable property. The reverse is also
    accepted because the effective product binds nullable source access to
    non-null slots and relies on the runtime guard; refusing it here would break
    existing graph definitions.
    """
    return (
        expected == actual
        or (isinstance(expected, NullableType) and expected.value == actual)
        or (isinstance(actual, NullableType) and actual.value == expected)
    )


def _property_values[
    C: Node | Edge[Any, Any],
](value: C, *, target: type[C]) -> PropertyValues:
    """Normalize a component instance into an immutable property tuple.

    ``value`` is read but never written. Every declared property must be present
    and must resolve to a value selection or expression of a compatible type.
    """
    if not isinstance(value, target):
        raise TypeError(f"properties must be an instance of {target.__name__}")
    declarations = properties_for(target)
    extra = set(vars(value)) - set(declarations)
    if extra:
        names = ", ".join(sorted(extra))
        raise TypeError(
            f"{target.__name__} has no declared property {names}"
        )
    result: list[tuple[str, ValueExpression[Any]]] = []
    for attribute, declaration in declarations.items():
        try:
            supplied = getattr(value, attribute)
        except AttributeError as error:
            raise TypeError(
                f"{target.__name__}.{attribute} must be assigned a value "
                "selection or expression"
            ) from error
        try:
            expression = as_expression(supplied)
        except TypeError as error:
            raise TypeError(
                f"{target.__name__}.{attribute} must be assigned a value "
                "selection or expression"
            ) from error
        if not _compatible(declaration.logical_type, expression.logical_type):
            raise TypeError(
                f"{target.__name__}.{attribute} expects "
                f"{declaration.logical_type!r}, but the expression resolves to "
                f"{expression.logical_type!r}"
            )
        result.append((declaration.name or attribute, expression))
    return tuple(sorted(result, key=lambda item: item[0]))


def _as_row_source(value: Any) -> Any:
    """Accept both a row-source value and the historical declaration class form."""
    if isinstance(value, type):
        factory = getattr(value, "row_source", None)
        if not callable(factory):
            raise TypeError(
                "rows must be a row source value or a Table/Projection "
                "declaration; use Table.row_source()"
            )
        value = factory()
    try:
        return as_row_source(value)
    except TypeError as error:
        raise TypeError(
            "rows must be a row source value or a Table/Projection declaration; "
            "use Table.row_source()"
        ) from error


def _require_concrete_component(target: Any, kind: str) -> None:
    if (
        not isinstance(target, type)
        or component_kind(target) != kind
        or is_abstract_component(target)
    ):
        name = getattr(target, "__name__", repr(target))
        raise TypeError(f"target must be a concrete {kind} component, not {name}")


def _declared_endpoints(target: type[Any]) -> tuple[type[Node], type[Node]]:
    """Read the two node categories an edge declares.

    The authoring topology model records them in ``_metadata``; the fallbacks
    keep the factory usable with a declaration implementation that stores the
    pair on a named class attribute.
    """
    metadata = getattr(target, "_metadata", None)
    if isinstance(metadata, Mapping):
        source = metadata.get("source")
        declared_target = metadata.get("target")
        if isinstance(source, type) and isinstance(declared_target, type):
            return source, declared_target
    for source_attribute, target_attribute in (
        ("_source", "_target"),
        ("_component_source", "_component_target"),
    ):
        source = getattr(target, source_attribute, None)
        declared_target = getattr(target, target_attribute, None)
        if isinstance(source, type) and isinstance(declared_target, type):
            return source, declared_target
    raise TypeError(f"{target.__name__} does not declare edge endpoints")


def _resolve_endpoint(
    token: Any, *, declared: Any, side: str,
) -> type[Node] | None:
    """Each endpoint token is required exactly when its declared endpoint is abstract."""
    declared_is_abstract = bool(
        isinstance(declared, type) and is_abstract_component(declared)
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
            f"{side}_node must be an endpoint(...) token, not the raw value "
            f"{token!r}"
        )
    selected = token.target
    if (
        not isinstance(selected, type)
        or component_kind(selected) != "node"
        or is_abstract_component(selected)
    ):
        name = getattr(selected, "__name__", repr(selected))
        raise TypeError(
            f"{side}_node must name a concrete node component, not {name}"
        )
    if not issubclass(selected, declared):
        raise TypeError(
            f"{side}_node {selected.__name__} must equal or descend from the "
            f"declared endpoint category {declared.__name__}"
        )
    return selected


@overload
def node_binding[N: Node, S: Shape](
    *, target: type[N],
    rows: type[S] | DerivedRowSource[S] | RelationRowSource[S],
    bind: Callable[[S], NodeValues[N, Any]],
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
            raise TypeError(
                "node_binding takes either build_key/properties or rows/bind"
            )
        if rows is None or bind is None:
            raise TypeError("rows and bind must be supplied together")
        rows = _as_row_source(rows)
        values = bind(shape_context(rows.shape))
        if not isinstance(values, NodeValues):
            raise TypeError("node_binding bind must return NodeValues")
        build_key, properties = values.build_key, values.properties
    elif build_key is None or properties is None:
        raise TypeError(
            "node_binding requires build_key and properties, or rows and bind"
        )
    return NodeBinding(
        debug_name,
        target,
        _require_key(build_key, argument="build_key"),
        _property_values(properties, target=target),
        tuple(options.annotations),
        rows,
    )


@overload
def edge_binding[E: Edge[Any, Any], S: Shape](
    *, target: type[E],
    rows: type[S] | DerivedRowSource[S] | RelationRowSource[S],
    bind: Callable[[S], EdgeValues[E, Any, Any, Any]],
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
    E: Edge[Any, Any], S: Node, DC: NodeSideBase, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[S, DC]], target_node: Endpoint[DC],
    build_key: ValueInput[Key], source_build_key: ValueInput[SourceKey],
    target_build_key: ValueInput[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...


@overload
def edge_binding[
    E: Edge[Any, Any], SC: NodeSideBase, D: Node, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[SC, D]], source_node: Endpoint[SC],
    build_key: ValueInput[Key], source_build_key: ValueInput[SourceKey],
    target_build_key: ValueInput[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...


@overload
def edge_binding[
    E: Edge[Any, Any], SC: NodeSideBase, DC: NodeSideBase,
    Key: NonNullableGraphValue, SourceKey: NonNullableGraphValue,
    TargetKey: NonNullableGraphValue,
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
            raise TypeError(
                "edge_binding takes either key/properties or rows/bind"
            )
        if rows is None or bind is None:
            raise TypeError("rows and bind must be supplied together")
        rows = _as_row_source(rows)
        values = bind(shape_context(rows.shape))
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
    declared_source, declared_target = _declared_endpoints(target)
    return EdgeBinding(
        debug_name,
        target,
        _require_key(build_key, argument="build_key"),
        _require_key(source_build_key, argument="source_build_key"),
        _require_key(target_build_key, argument="target_build_key"),
        _property_values(properties, target=target),
        tuple(options.annotations),
        _resolve_endpoint(source_node, declared=declared_source, side="source"),
        _resolve_endpoint(target_node, declared=declared_target, side="target"),
        rows,
    )


__all__ = ["edge_binding", "node_binding"]
