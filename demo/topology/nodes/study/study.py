from kg_build_system import Node, NodeOptions, PropertySlot, property

from demo.topology.templates.named import NamedGraphComponentTemplate


class StudyNode(NamedGraphComponentTemplate, Node):
    """A study that provides evidence provenance."""

    options = NodeOptions()
    description: PropertySlot[str | None] = property()
