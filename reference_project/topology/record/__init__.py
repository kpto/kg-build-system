from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class RecordNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Record"),))

    title: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
