from demo.topology.templates.named import NamedGraphComponentTemplate
from kg_build_system import PropertySlot, node, property


@node(description="A disease or phenotype.")
class DiseaseNode(NamedGraphComponentTemplate):
    description: PropertySlot[str | None] = property()
