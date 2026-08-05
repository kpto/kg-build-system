from kg_build_system import GraphComponent, PropertySlot, node, property


@node(description="A disease or phenotype.")
class Disease(GraphComponent):
    name: PropertySlot[str] = property(name="name", nullable=False)
