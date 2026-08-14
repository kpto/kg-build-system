from kg_build_system import Projection, projection_field
from demo.table.evidence_release.pharmacogenomics.association import AssociationTable


class AssociationEvidenceProjection(Projection):
    """One logical evidence-label row, derived from an association contract."""

    target_id = projection_field(AssociationTable.target_id.when_present())
    target_symbol = projection_field(AssociationTable.target_symbol.or_else("Unknown symbol"))
    disease_id = projection_field(
        AssociationTable.evidence.each().pick(lambda evidence: evidence.disease_id)
    )
    evidence_label = projection_field(
        AssociationTable.evidence.each().pick(lambda evidence: evidence.labels).each()
    )
    study_id = projection_field(AssociationTable.study_id.or_else("Unknown study"))
    score = projection_field(AssociationTable.score.or_else(0.0))
