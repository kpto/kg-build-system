"""Author-facing binding factories.

``node_binding`` maps a row context onto one concrete node and ``edge_binding``
maps it onto one concrete edge. Each accepts a direct key/properties form or a
row-derived ``rows``/``bind`` form.

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
from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast, overload

from kg_build_system.distribution.languages.expressions.model.public import (
    ValueInput,
)
from kg_build_system.distribution.languages.table.model.public import (
    DerivedRowSource,
    RelationRowSource,
)
from kg_build_system.distribution.languages.topology.model.public import (
    Edge, Endpoint, Node, NodeSideBase, NonNullableGraphValue,
)
from kg_build_system.kernel.model.public.types import Shape
from ...model.public.values import (
    BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
)
from ..internal.factories import edge_binding as edge_binding_impl
from ..internal.factories import node_binding as node_binding_impl


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
    row-derived form, ``rows`` plus ``bind``. The two forms are exclusive.

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

    binding = node_binding(
        target=UnitNode,
        build_key=UnitTable.unit_ref,
        properties=UnitNode(name=UnitTable.unit_name),
    )
    ```
    """
    return cast(Any, node_binding_impl)(
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
    row-derived form, ``rows`` plus ``bind``. ``source_node`` and
    ``target_node`` are ``endpoint(...)`` tokens required by an abstract
    declared endpoint and optional otherwise.

    Example:
    ```python
    from kg_build_system import (
        Edge, Field, Node, PropertySlot, Table, edge_binding, field, property,
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

    binding = edge_binding(
        target=HasUnitEdge,
        build_key=UnitTable.unit_ref,
        source_build_key=UnitTable.site_id,
        target_build_key=UnitTable.unit_ref,
        properties=HasUnitEdge(as_at=UnitTable.as_at),
    )
    ```
    """
    return cast(Any, edge_binding_impl)(
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


__all__ = ["edge_binding", "node_binding"]
