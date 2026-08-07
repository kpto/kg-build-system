from kg_build_system import bind, node_binding, value

from demo.table.contracts.reference import DiseaseTable
from demo.topology.nodes.disease.disease import DiseaseNode


disease_from_reference = node_binding(
    debug_name="disease_from_reference",
    target=DiseaseNode,
    build_key=bind(value.concat("disease::", DiseaseTable.disease_id)),
    properties=DiseaseNode(
        name=bind(DiseaseTable.name),
        description=bind(DiseaseTable.description),
    ),
)
