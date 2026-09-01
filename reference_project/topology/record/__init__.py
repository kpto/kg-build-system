from reference_project.topology._common import Documented, Provenanced

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class RecordNode(Provenanced, Documented, Node):
    options = NodeOptions(annotations=(NodeLabel("Record"),))

    title: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
