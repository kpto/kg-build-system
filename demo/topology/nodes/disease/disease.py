from kg_build_system import node

from demo.topology.templates.named import NamedGraphComponent


@node(description="A disease or phenotype.")
class Disease(NamedGraphComponent):
    pass
