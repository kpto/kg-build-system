from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property

from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class SiteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"),))

    name: PropertySlot[str] = property()
    """The site's display name."""

    city: PropertySlot[str] = property()
    """City the premises is located in."""
