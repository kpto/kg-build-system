from kg_build_system import ProjectedField, Projection, collection, projected_field
from demo.table.evidence_release.pharmacogenomics.association import AssociationTable


class AssociationEvidenceProjection(Projection):
    """One logical evidence-label row, derived from an association contract."""

    target_id: ProjectedField[str] = projected_field(AssociationTable.target_id)
    target_symbol: ProjectedField[str] = projected_field(AssociationTable.target_symbol)
    disease_id: ProjectedField[str] = projected_field(
        collection.expand(AssociationTable.evidence.e.disease_id)
    )
    evidence_label: ProjectedField[str] = projected_field(
        collection.expand(AssociationTable.evidence.e.labels)
    )
    study_id: ProjectedField[str] = projected_field(AssociationTable.study_id)
    score: ProjectedField[float] = projected_field(AssociationTable.score)
