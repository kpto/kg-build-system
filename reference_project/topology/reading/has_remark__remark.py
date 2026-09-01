"""Reading -[:HAS_REMARK]-> Remark, a second child of the monitored-relation
category narrowed to a different concrete endpoint pair."""

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, TrackedRelationEdgeTemplate,
)
from reference_project.topology.reading import ReadingNode
from reference_project.topology.remark import RemarkNode

from kg_build_system import Edge, EdgeLabel, EdgeOptions


class HasRemarkEdge(
    TrackedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[ReadingNode, RemarkNode]
):
    """Relates a reading to one of its remarks."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_REMARK"),))
