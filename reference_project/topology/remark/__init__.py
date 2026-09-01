from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class RemarkNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A free-text remark recorded against a single equipment reading."""

    options = NodeOptions(annotations=(NodeLabel("Remark"),))

    text: PropertySlot[str] = property()
    """The content of the remark."""
