"""Record -[:CONTAINS_METRIC]-> Metric, descended under the derived-relation
category with both endpoint categories narrowed to the concrete components."""

from reference_project.topology.common import (
    DerivedRelationAbstractEdge, TrackedRelationEdgeTemplate,
)
from reference_project.topology.metric import MetricNode
from reference_project.topology.record import RecordNode

from kg_build_system import Edge, EdgeLabel, EdgeOptions


class ContainsMetricEdge(
    TrackedRelationEdgeTemplate, DerivedRelationAbstractEdge, Edge[RecordNode, MetricNode]
):
    """Relates a record to one of its measurements."""

    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS_METRIC"),))
