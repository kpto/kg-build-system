from kg_build_system import ProjectedField, collection, projected_field, projection

from demo.data.contracts.association import Association


@projection
class AssociationEvidence:
    """One logical evidence-label row, derived from an association contract."""

    target_id: ProjectedField[str] = projected_field(Association.target_id)
    target_symbol: ProjectedField[str] = projected_field(Association.target_symbol)
    disease_id: ProjectedField[str] = projected_field(
        collection.expand(Association.evidence.element.disease_id)
    )
    evidence_label: ProjectedField[str] = projected_field(
        collection.expand(Association.evidence.element.labels)
    )
    study_id: ProjectedField[str] = projected_field(Association.study_id)
    score: ProjectedField[float] = projected_field(Association.score)
