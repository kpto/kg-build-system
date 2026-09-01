from reference_project.topology._common import Documented, Provenanced

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class MetricNode(Provenanced, Documented, Node):
    options = NodeOptions(annotations=(NodeLabel("Metric"),))

    label: PropertySlot[str] = property()
    adjusted_value: PropertySlot[float] = property()
    disabled: PropertySlot[bool] = property()
