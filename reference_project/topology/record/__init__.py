from reference_project.topology._common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class RecordNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Record"),))

    title: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
