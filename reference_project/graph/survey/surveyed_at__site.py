"""SurveyVisit -[:SURVEYED_AT]-> Site, from the survey document root."""

from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Limitation, Meaning, Purpose,
)

from reference_project.graph.common import (
    MonitoredRelationAbstractEdge, TimestampedRelationEdgeTemplate,
)
from reference_project.graph.site import SiteNode
from reference_project.graph.survey import SurveyVisitNode


class SurveyedAtEdge(
    TimestampedRelationEdgeTemplate, MonitoredRelationAbstractEdge,
    Edge[SurveyVisitNode, SiteNode],
):
    """Relates a survey to the site it was carried out at."""

    options = EdgeOptions(
        annotations=(EdgeLabel("SURVEYED_AT"),),
        meaning=Meaning(
            purpose=Purpose(
                "Find the site a survey visit was carried out at.",
                limitations=(
                    Limitation(
                        "The site comes from the survey document, not from the unit's register location."
                    ),
                ),
            ),
            claims=(
                Claim("The edge runs from the visit to the site."),
            ),
        ),
    )
