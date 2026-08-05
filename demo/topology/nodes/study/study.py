from kg_build_system import PropertySlot, node, property

from demo.topology.templates.named import NamedGraphComponentTemplate


@node(description="A study that provides evidence provenance.")
class StudyNode(NamedGraphComponentTemplate):
    description: PropertySlot[str | None] = property()
