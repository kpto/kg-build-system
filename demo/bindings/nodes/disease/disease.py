from kg_build_system import bind, node_binding, value

from demo.data.projections.association_evidence import AssociationEvidence
from demo.topology.nodes.disease.disease import Disease


disease_from_evidence = node_binding(
    debug_name="disease_from_evidence",
    target=Disease,
    build_key=value.concat("disease::", AssociationEvidence.disease_id),
    properties=Disease(name=bind(value.coalesce(AssociationEvidence.disease_id, "Unknown disease"))),
)
