from demo.topology.templates.named import NamedGraphComponentTemplate
from kg_build_system import Node, PropertySlot, property


class StudyNode(NamedGraphComponentTemplate, Node):
    """A study that provides evidence provenance."""

    description: PropertySlot[str | None] = property()
