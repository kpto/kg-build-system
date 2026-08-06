from kg_build_system import bind, edge_binding, lookup, value

from demo.table.contracts.study import StudyTable
from demo.table.projections.association_evidence import AssociationEvidenceProjection
from demo.topology.nodes.target.edges.associated_with_disease import AssociatedWithEdge


association_to_disease = edge_binding(
    debug_name="association_to_disease",
    target=AssociatedWithEdge,
    build_key=value.deterministic_uuid(
        value.concat(
            AssociationEvidenceProjection.target_id,
            AssociationEvidenceProjection.disease_id,
            AssociationEvidenceProjection.evidence_label,
        )
    ),
    source_build_key=value.concat("target::", AssociationEvidenceProjection.target_id),
    target_build_key=value.concat("disease::", AssociationEvidenceProjection.disease_id),
    properties=AssociatedWithEdge(
        score=bind(AssociationEvidenceProjection.score),
        study_name=bind(
            value.coalesce(
                lookup.one(
                    key=AssociationEvidenceProjection.study_id,
                    match=StudyTable.study_id,
                    value=StudyTable.details.m.name,
                    as_type=str,
                ),
                "Unknown study",
            )
        ),
        evidence_disease_id=bind(AssociationEvidenceProjection.disease_id),
        evidence_label=bind(AssociationEvidenceProjection.evidence_label),
    ),
)
