from kg_build_system import bind, edge_binding, lookup, value

from demo.data.contracts.study import Study
from demo.data.projections.association_evidence import AssociationEvidence
from demo.topology.nodes.target.edges.associated_with_disease import AssociatedWith


association_to_disease = edge_binding(
    debug_name="association_to_disease",
    target=AssociatedWith,
    build_key=value.deterministic_uuid(
        value.concat(
            AssociationEvidence.target_id,
            AssociationEvidence.disease_id,
            AssociationEvidence.evidence_label,
        )
    ),
    source_build_key=value.concat("target::", AssociationEvidence.target_id),
    target_build_key=value.concat("disease::", AssociationEvidence.disease_id),
    properties=AssociatedWith(
        score=bind(AssociationEvidence.score),
        study_name=bind(
            value.coalesce(
                lookup.one(
                    key=AssociationEvidence.study_id,
                    match=Study.study_id,
                    value=Study.details.name,
                    as_type=str,
                ),
                "Unknown study",
            )
        ),
        evidence_disease_id=bind(AssociationEvidence.disease_id),
        evidence_label=bind(AssociationEvidence.evidence_label),
    ),
)
