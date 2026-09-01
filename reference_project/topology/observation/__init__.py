from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property

from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class ObservationNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """One measurement taken while monitoring a defect."""

    options = NodeOptions(annotations=(NodeLabel("Observation"),))

    value: PropertySlot[float] = property()
    """The observed magnitude, whatever scale the method reports."""

    method: PropertySlot[str] = property()
    """How the observation was taken."""

    observed_on: PropertySlot[str] = property()
    """Date the observation was taken."""
