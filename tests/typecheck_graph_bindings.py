"""Static contract for selections and expressions at graph binding boundaries."""
import datetime
from typing import assert_type
from uuid import UUID

from kg_build_system import (
    Array, ArraySelection, Edge, EdgeBinding, Field, Node, NodeBinding,
    NullableSelection, PropertySlot, Struct, Table, ValueSelection,
    edge_binding, field, node_binding, property,
)
from kg_build_system.expressions import BoolExpression, StrExpression
from kg_build_system.types import Date, Nullable, Time, Timestamp, Uuid


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


class TagTable(Table):
    identifier: Field[str] = field()
    codes: Field[Array[str | None]] = field()
    optional_codes: Field[Array[str | None] | None] = field()


class TagNode(Node):
    codes: PropertySlot[Array[str]] = property()
    optional_codes: PropertySlot[Array[str] | None] = property()


# without_nulls drops the item nullability, keeping the array's own nullability.
assert_type(TagTable.codes, ArraySelection[Nullable[str]])
assert_type(TagTable.codes.without_nulls(), ArraySelection[str])
assert_type(TagTable.optional_codes.without_nulls(), NullableSelection[Array[str]])

# sorted keeps the array shape; join needs non-null items and yields a string
# whose nullability mirrors the array's.
assert_type(TagTable.codes.without_nulls().sorted(), ArraySelection[str])
assert_type(
    TagTable.optional_codes.without_nulls().sorted(), NullableSelection[Array[str]]
)
assert_type(TagTable.codes.without_nulls().join(","), ValueSelection[str])
assert_type(
    TagTable.optional_codes.without_nulls().join(","), NullableSelection[str]
)

tags = node_binding(
    target=TagNode,
    build_key=TagTable.identifier,
    properties=TagNode(
        codes=TagTable.codes.without_nulls(),
        optional_codes=TagTable.optional_codes.without_nulls(),
    ),
)
assert_type(tags, NodeBinding[TagNode])

tags_expression = node_binding(
    target=TagNode,
    build_key=TagTable.identifier.expression,
    properties=TagNode(
        codes=TagTable.codes.expression.without_nulls(),
        optional_codes=TagTable.optional_codes.without_nulls(),
    ),
)
assert_type(tags_expression, NodeBinding[TagNode])


class KeywordStruct(Struct):
    keyword_id: Field[str] = field()
    keyword_type: Field[str | None] = field()


class PredicateTable(Table):
    identifier: Field[str] = field()
    label: Field[str] = field()
    optional_label: Field[str | None] = field()
    keywords: Field[Array[KeywordStruct]] = field()
    optional_keywords: Field[Array[KeywordStruct] | None] = field()


class PredicateNode(Node):
    label: PropertySlot[str] = property()


# equals is a non-null string operation that yields a Boolean predicate.
assert_type(PredicateTable.label.expression.equals("TARGET"), BoolExpression)
# where_present narrows, then equals chains cleanly.
assert_type(
    PredicateTable.optional_label.where_present().expression.equals("TARGET"), BoolExpression,
)

# keep_if preserves the expression family it is applied to.
assert_type(PredicateTable.label.expression, StrExpression)
assert_type(
    PredicateTable.label.expression.keep_if(
        PredicateTable.identifier.expression.equals("TARGET")
    ),
    StrExpression,
)

# map_items projects an element member into an array of that member's type; a
# nullable member yields nullable items, and a nullable array stays nullable.
assert_type(
    PredicateTable.keywords.map_items(lambda item: item.keyword_id), ArraySelection[str],
)
assert_type(
    PredicateTable.keywords.map_items(lambda item: item.keyword_type),
    ArraySelection[Nullable[str]],
)
assert_type(
    PredicateTable.optional_keywords.map_items(lambda item: item.keyword_id),
    NullableSelection[Array[str]],
)

# The projected array, and a keep_if-filtered key, both bind as before.
predicated = node_binding(
    target=PredicateNode,
    build_key=PredicateTable.identifier.expression.keep_if(
        PredicateTable.label.expression.equals("TARGET")
    ),
    properties=PredicateNode(label=PredicateTable.label),
)
assert_type(predicated, NodeBinding[PredicateNode])

