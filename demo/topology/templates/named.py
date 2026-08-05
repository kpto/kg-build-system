"""A reusable semantic component shape for named graph entities."""

from kg_build_system import GraphComponent, PropertySlot, component_template, property


@component_template(description="A graph component with a required human-readable name.")
class NamedGraphComponentTemplate(GraphComponent):
    name: PropertySlot[str] = property()
