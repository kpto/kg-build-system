from demo.topology.templates.named import NamedGraphComponentTemplate
from kg_build_system import Node, PropertySlot, property


class DiseaseNode(NamedGraphComponentTemplate, Node):
    """A disease or phenotype."""

    description: PropertySlot[str | None] = property()
