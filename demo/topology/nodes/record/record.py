from kg_build_system import Node, PropertySlot, property


class RecordNode(Node):
    title: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
