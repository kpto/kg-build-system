"""Defect -[:OBSERVED_DURING]-> SurveyVisit, from the surveyed defect grain.

The destination is a documented thing that recorded the defect. It is declared
concretely rather than as the ``Documented`` category because the Neo4j target
maps both endpoints onto node ID spaces and rejects an abstract declared side;
a category-endpoint edge is only consumable by targets that take the per-binding
view, such as file output. The binding still names its destination explicitly
with an endpoint token, which stays valid for a concrete declared side.
"""

from kg_build_system import Edge, EdgeLabel, EdgeOptions

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.topology.defect import DefectNode
from reference_project.topology.survey import SurveyVisitNode


class ObservedDuringEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge,
    Edge[DefectNode, SurveyVisitNode],
):
    """Relates a defect to the event during which it was observed."""

    options = EdgeOptions(annotations=(EdgeLabel("OBSERVED_DURING"),))
