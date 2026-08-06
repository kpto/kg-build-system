from kg_build_system import Node, PropertySlot, property

from demo.topology.templates.named import NamedGraphComponentTemplate


class StudyNode(NamedGraphComponentTemplate, Node):
    """A study that provides evidence provenance."""

    description: PropertySlot[str | None] = property()
