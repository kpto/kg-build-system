from reference_project.topology._common import Documented, Provenanced

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class NoteNode(Provenanced, Documented, Node):
    options = NodeOptions(annotations=(NodeLabel("Note"),))

    text: PropertySlot[str] = property()
