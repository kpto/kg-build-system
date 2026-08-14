from kg_build_system import Node, PropertySlot, property


class MetricNode(Node):
    label: PropertySlot[str] = property()
    adjusted_value: PropertySlot[float] = property()
    disabled: PropertySlot[bool] = property()
