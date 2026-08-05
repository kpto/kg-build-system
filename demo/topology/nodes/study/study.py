from kg_build_system import node

from demo.topology.templates.named import NamedGraphComponentTemplate


@node(description="A study that provides evidence provenance.")
class StudyNode(NamedGraphComponentTemplate):
    pass
