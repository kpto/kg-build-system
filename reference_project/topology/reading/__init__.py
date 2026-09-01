from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property

from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class ReadingNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """One measurement sample reported by a logger against a unit."""

    options = NodeOptions(annotations=(NodeLabel("Reading"),))

    value: PropertySlot[float | None] = property()
    """The measured value, absent when the logger reported no sample."""

    unit_of_measure: PropertySlot[str] = property()
    """The scale the value is expressed on, which differs by logger family."""

    recorded_on: PropertySlot[str] = property()
    """Date the sample was taken."""
