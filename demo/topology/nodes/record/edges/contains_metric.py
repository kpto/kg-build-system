from kg_build_system import Edge, EdgeLabel, EdgeOptions, PropertySlot, property

from demo.topology.nodes.metric.metric import MetricNode
from demo.topology.nodes.record.record import RecordNode


class ContainsMetricEdge(Edge[RecordNode, MetricNode]):
    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS_METRIC"),))

    city: PropertySlot[str] = property()
