from kg_build_system import Field, Table, field

from demo.table.templates.evidence import EvidenceStruct
from demo.table.templates.study import StudyReferenceTemplate


class AssociationTable(StudyReferenceTemplate, Table):
    """Concrete evidence input that reuses the shared study-reference contract."""

    target_id: Field[str] = field()
    target_symbol: Field[str] = field()
    evidence: Field[list[EvidenceStruct]] = field()
    score: Field[float] = field()
