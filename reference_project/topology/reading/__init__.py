from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class ReadingNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A single equipment reading, identified by its zone, unit, and code."""

    options = NodeOptions(annotations=(NodeLabel("Reading"),))

    name: PropertySlot[str] = property()
    """The reading's display name, naming its zone and code."""

    calibrated_value: PropertySlot[float] = property()
    """The reading's calibrated numeric value."""

    out_of_service: PropertySlot[bool] = property()
    """True while the measured equipment unit is out of service."""
