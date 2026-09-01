"""Unit -[:HAS_DEFECT]-> Defect, from the surveyed element grain."""

from kg_build_system import Edge, EdgeLabel, EdgeOptions

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.topology.defect import DefectNode
from reference_project.topology.unit import UnitNode


class HasDefectEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[UnitNode, DefectNode]
):
    """Relates equipment to a defect recorded against it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_DEFECT"),))
