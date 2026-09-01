from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property

from reference_project.topology.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class UnitNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A piece of installed equipment held on the asset register."""

    options = NodeOptions(annotations=(NodeLabel("Unit"),))

    name: PropertySlot[str] = property()
    """The equipment name as the register records it."""

    in_service: PropertySlot[bool] = property()
    """True while the equipment is in service."""

    survey_period: PropertySlot[str] = property()
    """The period the register last reviewed the equipment against."""
