from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class NoteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Note"),))

    text: PropertySlot[str] = property()
