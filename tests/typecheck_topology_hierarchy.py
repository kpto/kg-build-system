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


# A slot carrying the PEP 681 null default is optional for member bindings;
# slots without it stay required promises.
class TermCategory(AbstractNode):
    label: PropertySlot[str | None] = property(default=None)


class BareTerm(TermCategory, Node):
    code: PropertySlot[str] = property()


class NamedTerm(TermCategory, Node):
    code: PropertySlot[str] = property()


bare_term = node_binding(
    target=BareTerm,
    build_key=HierarchyTable.code,
    properties=BareTerm(code=HierarchyTable.code),
)
assert_type(bare_term, NodeBinding[BareTerm])

named_term = node_binding(
    target=NamedTerm,
    build_key=HierarchyTable.code,
    properties=NamedTerm(code=HierarchyTable.code, label=HierarchyTable.title),
)
assert_type(named_term, NodeBinding[NamedTerm])

record = node_binding(
    target=RecordNode,
    build_key=HierarchyTable.record_id.expression.prepend("record::"),
    properties=RecordNode(
        title=HierarchyTable.title,
        city=HierarchyTable.title,
        revision=HierarchyTable.record_id,
    ),
)
assert_type(record, NodeBinding[RecordNode])

# both endpoints declared as categories: both tokens required
both = edge_binding(
    target=RelatesEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    build_key=HierarchyTable.record_id,
    source_build_key=HierarchyTable.record_id,
    target_build_key=HierarchyTable.code,
    properties=RelatesEdge(),
)
assert_type(both, EdgeBinding[RelatesEdge])

# descended edge: only the still-abstract source side needs a token
descended = edge_binding(
    target=ContainsMetricEdge,
    source_node=endpoint(RecordNode),
    build_key=HierarchyTable.record_id,
    source_build_key=HierarchyTable.record_id,
    target_build_key=HierarchyTable.code,
    properties=ContainsMetricEdge(),
)
assert_type(descended, EdgeBinding[ContainsMetricEdge])


class DirectEdge(Edge[RecordNode, MetricNode]):
    """Both endpoints concrete: both tokens omittable."""


class MixedEdge(Edge[EntityNode, MetricNode]):
    """Only the source endpoint is abstract."""


omitted = edge_binding(
    target=DirectEdge,
    build_key=HierarchyTable.record_id,
    source_build_key=HierarchyTable.record_id,
    target_build_key=HierarchyTable.code,
    properties=DirectEdge(),
)
assert_type(omitted, EdgeBinding[DirectEdge])

explicit = edge_binding(
    target=DirectEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    build_key=HierarchyTable.record_id,
    source_build_key=HierarchyTable.record_id,
    target_build_key=HierarchyTable.code,
    properties=DirectEdge(),
)
assert_type(explicit, EdgeBinding[DirectEdge])

mixed = edge_binding(
    target=MixedEdge,
    source_node=endpoint(RecordNode),
    build_key=HierarchyTable.record_id,
    source_build_key=HierarchyTable.record_id,
    target_build_key=HierarchyTable.code,
    properties=MixedEdge(),
)
assert_type(mixed, EdgeBinding[MixedEdge])
