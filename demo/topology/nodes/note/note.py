from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class NoteNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Note"),))

    text: PropertySlot[str] = property()
