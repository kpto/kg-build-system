from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property
from kg_build_system.types import Timestamp

from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class SurveyVisitNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A condition survey carried out at a site on one date."""

    options = NodeOptions(annotations=(NodeLabel("SurveyVisit"),))

    surveyed_on: PropertySlot[Timestamp | None] = property()
    """Date the survey was carried out, absent when the feed records none."""

    surveyor: PropertySlot[str] = property()
    """Who carried out the survey."""

    practice: PropertySlot[str | None] = property()
    """The accredited practice the surveyor belongs to, when the feed records it."""
