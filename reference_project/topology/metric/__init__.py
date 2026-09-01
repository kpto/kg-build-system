from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)

from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class MetricNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A single measurement of a record, identified by its group and code."""

    options = NodeOptions(annotations=(NodeLabel("Metric"),))

    label: PropertySlot[str] = property()
    """The measurement's display name, naming its group and code."""

    adjusted_value: PropertySlot[float] = property()
    """The measurement's adjusted numeric value."""

    disabled: PropertySlot[bool] = property()
    """True when the measurement is deactivated."""
