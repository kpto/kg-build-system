"""A reusable semantic component shape for named graph entities."""

from kg_build_system import GraphComponent, PropertySlot, property


class NamedGraphComponentTemplate(GraphComponent):
    """A graph component with a required human-readable name."""
    name: PropertySlot[str] = property()
