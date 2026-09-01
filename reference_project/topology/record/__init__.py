from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class RecordNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A record: the entity a set of measurements and remarks belongs to."""

    options = NodeOptions(annotations=(NodeLabel("Record"),))

    title: PropertySlot[str] = property()
    """The record's display title."""

    city: PropertySlot[str] = property()
    """City where the record's contact is located."""
