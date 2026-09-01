"""Site -[:HAS_UNIT]-> Unit, from the equipment register."""

from kg_build_system import Edge, EdgeLabel, EdgeOptions

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.topology.site import SiteNode
from reference_project.topology.unit import UnitNode


class HasUnitEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[SiteNode, UnitNode]
):
    """Relates a site to equipment installed at it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
