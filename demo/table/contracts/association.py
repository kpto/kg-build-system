from kg_build_system import CollectionField, Field, Table, collection_field, field

from demo.table.templates.evidence import EvidenceStruct
from demo.table.templates.study import StudyReferenceTemplate


class AssociationTable(StudyReferenceTemplate, Table):
    """Concrete evidence input that reuses the shared study-reference contract."""

    target_id: Field[str] = field()
    target_symbol: Field[str] = field()
    evidence: CollectionField[EvidenceStruct] = collection_field()
    score: Field[float] = field()
