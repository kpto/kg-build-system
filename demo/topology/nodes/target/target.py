from kg_build_system import Node, NodeOptions, PropertySlot, property


class TargetNode(Node):
    """A biological target."""

    options = NodeOptions()
    symbol: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()
