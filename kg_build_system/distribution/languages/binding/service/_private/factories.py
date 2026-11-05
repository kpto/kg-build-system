"""Validated graph-binding factories: target, keys, values and endpoints."""
from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, overload

from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    as_expression, select_expression,
)
from kg_build_system.distribution.languages.data.model.public import (
    DerivedRowSource,
    RelationRowSource,
)
from kg_build_system.distribution.languages.data.service.internal.rows import (
    as_row_source,
)
from kg_build_system.distribution.languages.data.service.internal import (
    shape_context,
)
from kg_build_system.distribution.languages.topology.model.public import (
    Edge, Endpoint, Node, NodeSideBase, NonNullableGraphValue,
)
from kg_build_system.distribution.languages.topology.service.internal.metadata import (
    component_kind, is_abstract_component, metadata_for, properties_for,
)
from kg_build_system.kernel.model.public.types import NullableType, Shape
from kg_build_system.kernel.service.internal.types import (
    require_non_nullable, require_scalar,
)
from ...model.public.values import (
    BindingOptions,
    EdgeBinding,
    EdgeValues,
    NodeBinding,
    NodeValues,
    PropertyValues,
    PythonRef,
)


def _require_key(value: object, *, argument: str) -> Selection[Any]:
    try:
        selection = (
            value if isinstance(value, Selection)
            else select_expression(as_expression(value))
        )
    except TypeError as error:
        raise TypeError(
            f"{argument} must be a selection"
        ) from error
    require_non_nullable(
        require_scalar(selection.logical_type, context=argument),
        context=argument,
    )
    return selection


def _compatible(expected: object, actual: object) -> bool:
    """Compare a declared property type with the supplied expression type."""
    return (
        expected == actual
        or (isinstance(expected, NullableType) and expected.value == actual)
        or (isinstance(actual, NullableType) and actual.value == expected)
    )


def _property_values[
    C: Node | Edge[Any, Any],
](value: C, *, target: type[C]) -> PropertyValues:
    """Normalize a component instance into an immutable property tuple."""
    if not isinstance(value, target):
        raise TypeError(f"properties must be an instance of {target.__name__}")
    declarations = properties_for(target)
    extra = set(vars(value)) - set(declarations)
    if extra:
        names = ", ".join(sorted(extra))
        raise TypeError(
            f"{target.__name__} has no declared property {names}"
        )
    result: list[tuple[str, Selection[Any]]] = []
    for attribute, declaration in declarations.items():
        try:
            supplied = getattr(value, attribute)
        except AttributeError as error:
            raise TypeError(
                f"{target.__name__}.{attribute} must be assigned a value "
                "selection or expression"
            ) from error
        try:
            selection = (
                supplied if isinstance(supplied, Selection)
                else select_expression(as_expression(supplied))
            )
        except TypeError as error:
            raise TypeError(
                f"{target.__name__}.{attribute} must be assigned a selection"
            ) from error
        if not _compatible(declaration.logical_type, selection.logical_type):
            raise TypeError(
                f"{target.__name__}.{attribute} expects "
                f"{declaration.logical_type!r}, but the selection resolves to "
                f"{selection.logical_type!r}"
            )
        result.append((declaration.name or attribute, selection))
    return tuple(sorted(result, key=lambda item: item[0]))


def _as_row_source(value: Any) -> Any:
    """Require a row-source value; the declaration class is not accepted."""
    try:
        return as_row_source(value)
    except TypeError as error:
        raise TypeError(
            "rows must be a row source value; use Table.row_source() or "
            "Projection.row_source()"
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
    """Read the two node categories an edge declares."""
    metadata = metadata_for(target)
    if (
        metadata is not None
        and isinstance(metadata.source, type)
        and isinstance(metadata.target, type)
    ):
        return metadata.source, metadata.target
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


def _python_reference(value: Any) -> PythonRef | None:
    """Return the stable reference of a rows-form callable, if it names one."""
    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if not isinstance(module, str) or not module:
        return None
    if not isinstance(qualname, str) or not qualname:
        return None
    recorded = getattr(value, "__kbs_signature__", None)
    if isinstance(recorded, str):
        return PythonRef(module, qualname, recorded)
    try:
        signature = str(inspect.signature(value))
    except (TypeError, ValueError):
        signature = "(...)"
    return PythonRef(module, qualname, signature)


@overload
def node_binding[N: Node, S: Shape](
    *, target: type[N],
    rows: DerivedRowSource[S] | RelationRowSource[S],
    bind: Callable[[S], NodeValues[N, Any]],
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]: ...


@overload
def node_binding[N: Node, Key: NonNullableGraphValue](
    *, target: type[N], build_key: Selection[Key], properties: N,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]: ...


def node_binding[N: Node](
    *, target: type[N], build_key: Selection[Any] | None = None,
    properties: Any = None, rows: Any = None, bind: Any = None,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]:
    """Validate a node declaration into a frozen :class:`NodeBinding`."""
    _require_concrete_component(target, "node")
    mode = "declarative"
    reference: PythonRef | None = None
    if rows is not None or bind is not None:
        if build_key is not None or properties is not None:
            raise TypeError(
                "node_binding takes either build_key/properties or rows/bind"
            )
        if rows is None or bind is None:
            raise TypeError("rows and bind must be supplied together")
        rows = _as_row_source(rows)
        reference = _python_reference(bind)
        values = bind(shape_context(rows.shape))
        if not isinstance(values, NodeValues):
            raise TypeError("node_binding bind must return NodeValues")
        build_key, properties = values.build_key, values.properties
        mode = "python"
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
        mode=mode,  # type: ignore[arg-type]
        python_ref=reference,
    )


@overload
def edge_binding[E: Edge[Any, Any], S: Shape](
    *, target: type[E],
    rows: DerivedRowSource[S] | RelationRowSource[S],
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
    *, target: type[Edge[S, D]], build_key: Selection[Key],
    source_build_key: Selection[SourceKey],
    target_build_key: Selection[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...


@overload
def edge_binding[
    E: Edge[Any, Any], S: Node, DC: NodeSideBase, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[S, DC]], target_node: Endpoint[DC],
    build_key: Selection[Key], source_build_key: Selection[SourceKey],
    target_build_key: Selection[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...


@overload
def edge_binding[
    E: Edge[Any, Any], SC: NodeSideBase, D: Node, Key: NonNullableGraphValue,
    SourceKey: NonNullableGraphValue, TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[SC, D]], source_node: Endpoint[SC],
    build_key: Selection[Key], source_build_key: Selection[SourceKey],
    target_build_key: Selection[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...


@overload
def edge_binding[
    E: Edge[Any, Any], SC: NodeSideBase, DC: NodeSideBase,
    Key: NonNullableGraphValue, SourceKey: NonNullableGraphValue,
    TargetKey: NonNullableGraphValue,
](
    *, target: type[Edge[SC, DC]], source_node: Endpoint[SC],
    target_node: Endpoint[DC], build_key: Selection[Key],
    source_build_key: Selection[SourceKey],
    target_build_key: Selection[TargetKey], properties: E,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
) -> EdgeBinding[E]: ...


def edge_binding(
    *, target: type[Edge[Any, Any]], build_key: Selection[Any] | None = None,
    source_build_key: Selection[Any] | None = None,
    target_build_key: Selection[Any] | None = None, properties: Any = None,
    rows: Any = None, bind: Any = None,
    debug_name: str | None = None, options: BindingOptions = BindingOptions(),
    source_node: Endpoint[Any] | None = None,
    target_node: Endpoint[Any] | None = None,
) -> EdgeBinding[Any]:
    """Validate an edge declaration into a frozen :class:`EdgeBinding`."""
    _require_concrete_component(target, "edge")
    mode = "declarative"
    reference: PythonRef | None = None
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
        reference = _python_reference(bind)
        values = bind(shape_context(rows.shape))
        if not isinstance(values, EdgeValues):
            raise TypeError("edge_binding bind must return EdgeValues")
        build_key, properties = values.build_key, values.properties
        source_build_key, target_build_key = (
            values.source_build_key, values.target_build_key,
        )
        mode = "python"
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
        mode=mode,  # type: ignore[arg-type]
        python_ref=reference,
    )


__all__ = ["edge_binding", "node_binding"]
