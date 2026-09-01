from reference_project.topology._common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class MetricNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Metric"),))

    label: PropertySlot[str] = property()
    adjusted_value: PropertySlot[float] = property()
    disabled: PropertySlot[bool] = property()
