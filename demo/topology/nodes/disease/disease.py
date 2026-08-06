from demo.topology.templates.named import NamedGraphComponentTemplate
from kg_build_system import Node, NodeOptions, PropertySlot, property


class DiseaseNode(NamedGraphComponentTemplate, Node):
    """A disease or phenotype."""

    options = NodeOptions()
    description: PropertySlot[str | None] = property()
