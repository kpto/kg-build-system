"""Static contract for selections and expressions at graph binding boundaries."""
import datetime
from typing import assert_type
from uuid import UUID

from kg_build_system import (
    Edge, EdgeBinding, Field, Node, NodeBinding, PropertySlot, Table,
    edge_binding, field, node_binding, property,
)
from kg_build_system.types import Date, Time, Timestamp, Uuid


class BindingTable(Table):
    identifier: Field[str] = field()
    label: Field[str] = field()
    description: Field[str | None] = field()
    score: Field[float] = field()


class EntityNode(Node):
    label: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()


class RelatedEdge(Edge[EntityNode, EntityNode]):
    score: PropertySlot[float] = property()


node = node_binding(
    target=EntityNode,
    build_key=BindingTable.identifier,
    properties=EntityNode(
        label=BindingTable.label,
        description=BindingTable.description,
    ),
)
assert_type(node, NodeBinding[EntityNode])

narrowed = BindingTable.description.where_present()
narrowed_node = node_binding(
    target=EntityNode,
    build_key=narrowed,
    properties=EntityNode(label=narrowed, description=BindingTable.label),
)
assert_type(narrowed_node, NodeBinding[EntityNode])

edge = edge_binding(
    target=RelatedEdge,
    build_key=BindingTable.identifier.expression.prepend("edge:"),
    source_build_key=BindingTable.identifier,
    target_build_key=BindingTable.identifier,
    properties=RelatedEdge(score=BindingTable.score),
)
assert_type(edge, EdgeBinding[RelatedEdge])


class EventTable(Table):
    identifier: Field[str] = field()
    occurred: Field[Timestamp] = field()
    on: Field[Date | None] = field()
    at: Field[Time | None] = field()
    token: Field[Uuid] = field()


class EventNode(Node):
    occurred: PropertySlot[Timestamp] = property()
    on: PropertySlot[Date | None] = property()
    at: PropertySlot[Time | None] = property()
    token: PropertySlot[Uuid] = property()


class StdlibEventNode(Node):
    """Slots written with the stdlib classes are the same declarations."""

    occurred: PropertySlot[datetime.datetime] = property()
    token: PropertySlot[UUID] = property()


event = node_binding(
    target=EventNode,
    build_key=EventTable.identifier,
    properties=EventNode(
        occurred=EventTable.occurred,
        on=EventTable.on.where_present(),
        at=EventTable.at,
        token=EventTable.token.expression,
    ),
)
assert_type(event, NodeBinding[EventNode])

# a nullable temporal selection binds unchanged; a default keeps the unit type
defaulted_event = node_binding(
    target=EventNode,
    build_key=EventTable.identifier,
    properties=EventNode(
        occurred=EventTable.occurred,
        on=EventTable.on,
        at=EventTable.at.default_to(datetime.time(9, 30)),
        token=EventTable.token,
    ),
)
assert_type(defaulted_event, NodeBinding[EventNode])

stdlib_event = node_binding(
    target=StdlibEventNode,
    build_key=EventTable.identifier,
    properties=StdlibEventNode(
        occurred=EventTable.occurred,
        token=EventTable.token,
    ),
)
assert_type(stdlib_event, NodeBinding[StdlibEventNode])
