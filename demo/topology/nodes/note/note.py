from kg_build_system import Node, PropertySlot, property


class NoteNode(Node):
    text: PropertySlot[str] = property()
