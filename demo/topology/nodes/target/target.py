from kg_build_system import GraphComponent, PropertySlot, node, property


@node(description="A biological target.")
class Target(GraphComponent):
    symbol: PropertySlot[str] = property(name="symbol", nullable=False)
