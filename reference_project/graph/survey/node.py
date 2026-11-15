from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, property,
)
from kg_build_system import Timestamp

from reference_project.graph.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class SurveyVisitNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A condition survey carried out at a site on one date."""

    options = NodeOptions(
        annotations=(NodeLabel("SurveyVisit"),),
        meaning=Meaning(
            purpose=Purpose(
                "Place each reported defect in the visit whose document reported it.",
                limitations=(
                    Limitation(
                        "A visit is one inspection event, not the full maintenance history of the site."
                    ),
                ),
            ),
            claims=(
                Claim("The visit is identified by the survey document's identifier."),
            ),
        ),
    )

    surveyed_on: PropertySlot[Timestamp | None] = property(
        meaning=Meaning(
            claims=(Claim("The timestamp the survey document records for the visit."),),
        ),
    )

    surveyor: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The surveyor recorded on the survey document."),),
        ),
    )

    practice: PropertySlot[str | None] = property(
        meaning=Meaning(
            claims=(Claim("The surveying practice recorded on the document, when it names one."),),
        ),
    )
