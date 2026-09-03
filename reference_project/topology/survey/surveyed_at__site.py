"""SurveyVisit -[:SURVEYED_AT]-> Site, from the survey document root."""

from kg_build_system import Edge, EdgeLabel, EdgeOptions

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, TimestampedRelationEdgeTemplate,
)
from reference_project.topology.site import SiteNode
from reference_project.topology.survey import SurveyVisitNode


class SurveyedAtEdge(
    TimestampedRelationEdgeTemplate, MonitoredRelationAbstractEdge,
    Edge[SurveyVisitNode, SiteNode],
):
    """Relates a survey to the site it was carried out at."""

    options = EdgeOptions(annotations=(EdgeLabel("SURVEYED_AT"),))
