"""Internal interface of the graph-binding domain.

Another subpackage imports the frozen binding model, the validated factories,
the binding language and its part codec here. A graph author writes the names
re-exported by :mod:`kg_build_system.binding`; the compilation IR is
:mod:`kg_build_system.binding.ir`.

Every function here is a thin wrapper over its implementation, so this module
owns the documented interface rather than the implementation module.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast, overload

from ..expressions.interfaces import ValueInput
from ..table.interfaces import DerivedRowSource, RelationRowSource
from ..topology.interfaces import (
    Edge, Endpoint, Node, NodeSideBase, NonNullableGraphValue,
)
from ..types.interfaces import Shape
from .factories import (
    edge_binding as _edge_binding, node_binding as _node_binding,
)
from .ir import BindingIR, EdgeBindingIR, NodeBindingIR
from .language import (
    BindingLanguage,
    decode_binding as _decode_binding,
    decode_binding_part as _decode_binding_part,
    encode_binding as _encode_binding,
    encode_binding_part as _encode_binding_part,
)
from .models import (
    Binding, BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
    PropertyValues,
)


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
    """Validate one node binding and return its frozen value.

    Accepts either the direct form, ``build_key`` plus ``properties``, or the
    row-derived form, ``rows`` plus ``bind``. The two forms are exclusive and
    the returned value is the frozen data consumed by :func:`compile`.

    Example:
    ```python
    from kg_build_system import (
        Field, Node, NodeValues, PropertySlot, Table, field, node_binding,
        property,
    )

    class UnitTable(Table):
        unit_ref: Field[str] = field()
        unit_name: Field[str] = field()

    class UnitNode(Node):
        name: PropertySlot[str] = property()

    direct = node_binding(
        target=UnitNode,
        build_key=UnitTable.unit_ref,
        properties=UnitNode(name=UnitTable.unit_name),
    )
    from_rows = node_binding(
        target=UnitNode,
        rows=UnitTable.row_source(),
        bind=lambda row: NodeValues(
            build_key=row.unit_ref,
            properties=UnitNode(name=row.unit_name),
        ),
    )
    ```
    """
    # The implementation is overloaded by form; the passthrough supplies both.
    return cast(Any, _node_binding)(
        target=target,
        build_key=build_key,
        properties=properties,
        rows=rows,
        bind=bind,
        debug_name=debug_name,
        options=options,
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
    """Validate one edge binding and return its frozen value.

    Accepts either the direct form, the three keys plus ``properties``, or the
    row-derived form, ``rows`` plus ``bind``. The two forms are exclusive.
    ``source_node`` and ``target_node`` are ``endpoint(...)`` tokens required by
    an abstract declared endpoint and optional otherwise.

    Example:
    ```python
    from kg_build_system import (
        Edge, EdgeValues, Field, Node, PropertySlot, Table, edge_binding,
        field, property,
    )

    class UnitTable(Table):
        site_id: Field[str] = field()
        unit_ref: Field[str] = field()
        as_at: Field[str] = field()

    class SiteNode(Node):
        pass

    class UnitNode(Node):
        pass

    class HasUnitEdge(Edge[SiteNode, UnitNode]):
        as_at: PropertySlot[str] = property()

    direct = edge_binding(
        target=HasUnitEdge,
        build_key=UnitTable.unit_ref,
        source_build_key=UnitTable.site_id,
        target_build_key=UnitTable.unit_ref,
        properties=HasUnitEdge(as_at=UnitTable.as_at),
    )
    from_rows = edge_binding(
        target=HasUnitEdge,
        rows=UnitTable.row_source(),
        bind=lambda row: EdgeValues(
            build_key=row.unit_ref,
            source_build_key=row.site_id,
            target_build_key=row.unit_ref,
            properties=HasUnitEdge(as_at=row.as_at),
        ),
    )
    ```
    """
    # The implementation is overloaded by form; the passthrough supplies both.
    return cast(Any, _edge_binding)(
        target=target,
        build_key=build_key,
        source_build_key=source_build_key,
        target_build_key=target_build_key,
        properties=properties,
        rows=rows,
        bind=bind,
        debug_name=debug_name,
        options=options,
        source_node=source_node,
        target_node=target_node,
    )


def encode_binding(binding: BindingIR) -> dict[str, Any]:
    """Encode one binding IR value as its canonical JSON object.

    The result is the form :func:`decode_binding` accepts and is independent of
    the authoring classes that produced the IR.

    Example:
    ```python
    from kg_build_system.binding.interfaces import encode_binding
    from kg_build_system.binding.ir import NodeBindingIR
    from kg_build_system.expressions.ir import LiteralExpressionIR
    from kg_build_system.types.ir import UnitTypeIR

    key = LiteralExpressionIR(logical_type=UnitTypeIR("str"), value="unit-1")
    binding = NodeBindingIR(
        "binding:node:Unit:1", "Unit", key, (("name", key),),
    )
    payload = encode_binding(binding)
    ```
    """
    return _encode_binding(binding)


def decode_binding(value: Mapping[str, Any]) -> NodeBindingIR | EdgeBindingIR:
    """Decode one canonical binding object back into binding IR.

    The object is normally the result of :func:`encode_binding`; the returned
    value is a node or edge IR selected by its ``kind`` field.

    Example:
    ```python
    from kg_build_system.binding.interfaces import decode_binding

    restored = decode_binding(payload)
    ```
    """
    return _decode_binding(value)


def encode_binding_part(
    bindings: Sequence[BindingIR] | object,
) -> list[dict[str, Any]]:
    """Encode a binding part as a list of canonical JSON objects.

    ``bindings`` is normally the tuple of binding IR values from a blueprint;
    an object carrying a ``bindings`` attribute is accepted too.

    Example:
    ```python
    from kg_build_system.binding.interfaces import encode_binding_part

    part = encode_binding_part(blueprint.bindings)
    ```
    """
    return _encode_binding_part(bindings)


def decode_binding_part(value: list[dict[str, Any]]) -> tuple[BindingIR, ...]:
    """Decode a binding part produced by :func:`encode_binding_part`.

    The result is a tuple of node and edge binding IR values in document order.

    Example:
    ```python
    from kg_build_system.binding.interfaces import decode_binding_part

    bindings = decode_binding_part(document["binding"])
    ```
    """
    return _decode_binding_part(value)


__all__ = [
    "Binding", "BindingIR", "BindingLanguage", "BindingOptions", "EdgeBinding",
    "EdgeBindingIR", "EdgeValues", "NodeBinding", "NodeBindingIR", "NodeValues",
    "PropertyValues", "decode_binding", "decode_binding_part", "edge_binding",
    "encode_binding", "encode_binding_part", "node_binding",
]
