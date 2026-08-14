from kg_build_system import Edge, PropertySlot, property

from demo.topology.nodes.metric.metric import MetricNode
from demo.topology.nodes.record.record import RecordNode


class ContainsMetricEdge(Edge[RecordNode, MetricNode]):
    city: PropertySlot[str] = property()
