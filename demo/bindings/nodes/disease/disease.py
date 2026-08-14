from kg_build_system import node_binding

from demo.table.evidence_release.reference_data.disease import DiseaseTable
from demo.topology.nodes.disease.disease import DiseaseNode


disease_from_reference = node_binding(
    debug_name="disease_from_reference",
    target=DiseaseNode,
    build_key=DiseaseTable.disease_id.when_present().prepend("disease::"),
    properties=DiseaseNode(
        name=DiseaseTable.name.or_else("Unknown disease"),
        description=DiseaseTable.description,
    ),
)
