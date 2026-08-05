from kg_build_system import ProjectedField, collection, projected_field, projection

from demo.table.contracts.association import AssociationTable


@projection
class AssociationEvidenceProjection:
    """One logical evidence-label row, derived from an association contract."""

    target_id: ProjectedField[str] = projected_field(AssociationTable.target_id)
    target_symbol: ProjectedField[str] = projected_field(AssociationTable.target_symbol)
    disease_id: ProjectedField[str] = projected_field(
        collection.expand(AssociationTable.evidence.element.disease_id)
    )
    evidence_label: ProjectedField[str] = projected_field(
        collection.expand(AssociationTable.evidence.element.labels)
    )
    study_id: ProjectedField[str] = projected_field(AssociationTable.study_id)
    score: ProjectedField[float] = projected_field(AssociationTable.score)
