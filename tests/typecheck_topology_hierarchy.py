"""Static contract for the node/edge hierarchy and category endpoint bindings."""
from dataclasses import dataclass
from typing import assert_type

from kg_build_system import (
    AbstractEdge, AbstractNode, Edge, EdgeBinding, EdgeOptions, EdgeOptionsTemplate,
    EdgeTemplate, Field, Node, NodeBinding, NodeOptions, NodeOptionsTemplate,
    NodeTemplate, PropertySlot, Table, edge_binding, endpoint, field,
    node_binding, property,
)
from kg_build_system.annotations import Annotation


@dataclass(frozen=True)
class AuditTrail(Annotation):
    namespace = "typecheck_topology_hierarchy"
    annotation_id = "audit_trail"

    track: str


class HierarchyTable(Table):
    record_id: Field[str] = field()
    title: Field[str] = field()
    code: Field[str] = field()


class Audited(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(AuditTrail(track="audit"),))
    revision: PropertySlot[str] = property()


class Weighted(EdgeTemplate):
    options = EdgeOptionsTemplate(annotations=(AuditTrail(track="weight"),))


class EntityNode(AbstractNode):
    options = NodeOptions()
    title: PropertySlot[str] = property()


class RecordNode(Audited, EntityNode, Node):
    city: PropertySlot[str] = property()


class MetricNode(EntityNode, Node):
    code: PropertySlot[str] = property()


class RelatesEdge(Edge[EntityNode, EntityNode]):
    """Concrete edge with both endpoints declared as categories."""


class ContainsEdge(Weighted, AbstractEdge[EntityNode, EntityNode]):
    options = EdgeOptions()


class ContainsMetricEdge(ContainsEdge, Edge[EntityNode, MetricNode]):
    """Descended edge; the target category narrows to MetricNode."""


record = node_binding(
    target=RecordNode,
    build_key=HierarchyTable.record_id.alter_rows().drop_null().expression.prepend("record::"),
    properties=RecordNode(
        title=HierarchyTable.title.alter_rows().drop_null(),
        city=HierarchyTable.title.alter_rows().drop_null(),
        revision=HierarchyTable.record_id.alter_rows().drop_null(),
    ),
)
assert_type(record, NodeBinding[RecordNode])

# both endpoints declared as categories: both tokens required
both = edge_binding(
    target=RelatesEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    source_build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    target_build_key=HierarchyTable.code.alter_rows().drop_null(),
    properties=RelatesEdge(),
)
assert_type(both, EdgeBinding[RelatesEdge])

# descended edge: only the still-abstract source side needs a token
descended = edge_binding(
    target=ContainsMetricEdge,
    source_node=endpoint(RecordNode),
    build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    source_build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    target_build_key=HierarchyTable.code.alter_rows().drop_null(),
    properties=ContainsMetricEdge(),
)
assert_type(descended, EdgeBinding[ContainsMetricEdge])


class DirectEdge(Edge[RecordNode, MetricNode]):
    """Both endpoints concrete: both tokens omittable."""


class MixedEdge(Edge[EntityNode, MetricNode]):
    """Only the source endpoint is abstract."""


omitted = edge_binding(
    target=DirectEdge,
    build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    source_build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    target_build_key=HierarchyTable.code.alter_rows().drop_null(),
    properties=DirectEdge(),
)
assert_type(omitted, EdgeBinding[DirectEdge])

explicit = edge_binding(
    target=DirectEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    source_build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    target_build_key=HierarchyTable.code.alter_rows().drop_null(),
    properties=DirectEdge(),
)
assert_type(explicit, EdgeBinding[DirectEdge])

mixed = edge_binding(
    target=MixedEdge,
    source_node=endpoint(RecordNode),
    build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    source_build_key=HierarchyTable.record_id.alter_rows().drop_null(),
    target_build_key=HierarchyTable.code.alter_rows().drop_null(),
    properties=MixedEdge(),
)
assert_type(mixed, EdgeBinding[MixedEdge])
