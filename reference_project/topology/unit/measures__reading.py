"""Unit -[:MEASURES]-> Reading, from each telemetry partition."""

from kg_build_system import Edge, EdgeLabel, EdgeOptions

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.topology.reading import ReadingNode
from reference_project.topology.unit import UnitNode


class MeasuresEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[UnitNode, ReadingNode]
):
    """Relates equipment to a sample reported against it."""

    options = EdgeOptions(annotations=(EdgeLabel("MEASURES"),))
