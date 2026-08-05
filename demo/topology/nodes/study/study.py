from kg_build_system import GraphComponent, PropertySlot, node, property


@node(description="A study that provides evidence provenance.")
class StudyNode(GraphComponent):
    name: PropertySlot[str] = property(name="name", nullable=False)
