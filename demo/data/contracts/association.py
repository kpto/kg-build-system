from kg_build_system import Field, field, table

from demo.data.templates.evidence import EvidenceStruct
from demo.data.templates.study import StudyReferenceTemplate


@table()
class AssociationTable(StudyReferenceTemplate):
    """Concrete evidence input that reuses the shared study-reference contract."""

    target_id: Field[str] = field()
    target_symbol: Field[str] = field()
    evidence: Field[list[EvidenceStruct]] = field()
    score: Field[float] = field()
