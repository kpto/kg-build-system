"""Static contract for row sources, where and Boolean identities."""
from typing import assert_type

from kg_build_system import (
    DerivedRowSource, Field, Node, NodeBinding, NodeValues, Projection,
    PropertySlot, Table, all_of, any_of, field, node_binding, projection_field,
    property,
)
from kg_build_system.expressions import BoolExpression


class Source(Table):
    kind: Field[str] = field()
    status: Field[str] = field()


class SourceView(Projection):
    kind = projection_field(Source.kind)


class TargetNode(Node):
    label: PropertySlot[str] = property()


active = Source.where(lambda source: any_of(
    source.kind.expression.equals("target"),
    source.kind.expression.equals("disease"),
))
assert_type(active, DerivedRowSource[Source])

strict = active.where(lambda source: source.status.expression.equals("active"))
assert_type(strict, DerivedRowSource[Source])

projected = SourceView.where(
    lambda projection: projection.kind.expression.equals("target"),
)
assert_type(projected, DerivedRowSource[SourceView])

binding = node_binding(
    target=TargetNode,
    rows=active,
    bind=lambda row: NodeValues(
        build_key=row.status,
        properties=TargetNode(label=row.kind),
    ),
)
assert_type(binding, NodeBinding[TargetNode])

assert_type(any_of(), BoolExpression)
assert_type(all_of(), BoolExpression)
