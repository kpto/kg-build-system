"""Static contract for selections and expressions at graph binding boundaries."""
from typing import assert_type

from kg_build_system import (
    Edge, EdgeBinding, Field, Node, NodeBinding, PropertySlot, Table,
    edge_binding, field, node_binding, property,
)


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
