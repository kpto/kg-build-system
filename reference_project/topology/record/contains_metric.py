from reference_project.topology.nodes.metric.metric import MetricNode
from reference_project.topology.nodes.record.record import RecordNode

from kg_build_system import Edge, EdgeLabel, EdgeOptions, PropertySlot, property


class ContainsMetricEdge(Edge[RecordNode, MetricNode]):
    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS_METRIC"),))

    city: PropertySlot[str] = property()
