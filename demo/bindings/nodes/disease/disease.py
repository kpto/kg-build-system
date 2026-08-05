from kg_build_system import bind, node_binding, value

from demo.data.contracts.reference import DiseaseReference
from demo.topology.nodes.disease.disease import Disease


disease_from_reference = node_binding(
    debug_name="disease_from_reference",
    target=Disease,
    build_key=value.concat("disease::", DiseaseReference.disease_id),
    properties=Disease(name=bind(DiseaseReference.name)),
)
