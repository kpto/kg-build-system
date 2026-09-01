from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property

from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class DefectNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A defect recorded against an element during a survey."""

    options = NodeOptions(annotations=(NodeLabel("Defect"),))

    title: PropertySlot[str] = property()
    """What the defect is, as the surveyor described it."""

    condition_rating: PropertySlot[str] = property()
    """Condition grade assigned on the survey scale."""
