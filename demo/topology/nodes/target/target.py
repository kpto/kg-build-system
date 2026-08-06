from kg_build_system import Node, PropertySlot, property


class TargetNode(Node):
    """A biological target."""

    symbol: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()
