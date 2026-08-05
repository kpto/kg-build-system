from kg_build_system import GraphComponent, PropertySlot, node, property


@node(description="A biological target.")
class TargetNode(GraphComponent):
    symbol: PropertySlot[str] = property(nullable=False)
