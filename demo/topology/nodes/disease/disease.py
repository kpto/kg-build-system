from kg_build_system import node

from demo.topology.templates.named import NamedGraphComponentTemplate


@node(description="A disease or phenotype.")
class DiseaseNode(NamedGraphComponentTemplate):
    pass
