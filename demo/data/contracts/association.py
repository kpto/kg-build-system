from kg_build_system import Field, field, struct, table


@struct
class Evidence:
    disease_id: Field[str] = field(name="disease_id")
    labels: Field[list[str]] = field(name="labels")


@table(name="association")
class Association:
    target_id: Field[str] = field(name="target_id")
    target_symbol: Field[str] = field(name="target_symbol")
    study_id: Field[str] = field(name="study_id")
    evidence: Field[list[Evidence]] = field(name="evidence")
    score: Field[float] = field(name="score")
