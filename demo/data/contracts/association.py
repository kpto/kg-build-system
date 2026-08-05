from kg_build_system import Field, field, table

from demo.data.templates.evidence import Evidence
from demo.data.templates.study import StudyReference


@table(name="association")
class Association(StudyReference):
    """Concrete evidence input that reuses the shared study-reference contract."""

    target_id: Field[str] = field(name="target_id")
    target_symbol: Field[str] = field(name="target_symbol")
    evidence: Field[list[Evidence]] = field(name="evidence")
    score: Field[float] = field(name="score")
