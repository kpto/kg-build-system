from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class SiteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A monitored site: the premises a set of equipment readings belongs to."""

    options = NodeOptions(annotations=(NodeLabel("Site"),))

    name: PropertySlot[str] = property()
    """The site's display name."""

    city: PropertySlot[str] = property()
    """City the site is located in."""
