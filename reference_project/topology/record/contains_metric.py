from reference_project.topology.metric import MetricNode
from reference_project.topology.record import RecordNode

from kg_build_system import Edge, EdgeLabel, EdgeOptions, PropertySlot, property


class ContainsMetricEdge(Edge[RecordNode, MetricNode]):
    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS_METRIC"),))

    city: PropertySlot[str] = property()
