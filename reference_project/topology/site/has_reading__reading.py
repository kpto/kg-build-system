"""Site -[:HAS_READING]-> Reading, descended under the monitored-relation
category with both endpoint categories narrowed to the concrete components."""

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, TrackedRelationEdgeTemplate,
)
from reference_project.topology.reading import ReadingNode
from reference_project.topology.site import SiteNode

from kg_build_system import Edge, EdgeLabel, EdgeOptions


class HasReadingEdge(
    TrackedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[SiteNode, ReadingNode]
):
    """Relates a site to one of its equipment readings."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_READING"),))
