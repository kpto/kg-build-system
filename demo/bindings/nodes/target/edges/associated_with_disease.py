from kg_build_system import edge_binding

from demo.table.projections.association_evidence import AssociationEvidenceProjection
from demo.topology.nodes.target.edges.associated_with_disease import AssociatedWithEdge


association_to_disease = edge_binding(
    debug_name="association_to_disease",
    target=AssociatedWithEdge,
    build_key=(
        AssociationEvidenceProjection.target_id
        .prepend("association::")
        .append("::")
        .append(AssociationEvidenceProjection.disease_id)
        .append("::")
        .append(AssociationEvidenceProjection.evidence_label)
    ),
    source_build_key=AssociationEvidenceProjection.target_id.prepend("target::"),
    target_build_key=AssociationEvidenceProjection.disease_id.prepend("disease::"),
    properties=AssociatedWithEdge(
        score=AssociationEvidenceProjection.score,
        study_id=AssociationEvidenceProjection.study_id,
        evidence_disease_id=AssociationEvidenceProjection.disease_id,
        evidence_label=AssociationEvidenceProjection.evidence_label,
    ),
)
