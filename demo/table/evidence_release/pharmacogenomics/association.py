from kg_build_system import Array, Field, Struct, Table, TableOptions, field


class AssociationTableEvidenceStruct(Struct):
    disease_id: Field[str] = field(name='disease_id')
    labels: Field[Array[str]] = field(name='labels')


class AssociationTable(Table):
    options = TableOptions(name='association')
    target_id: Field[str | None] = field(name='target_id')
    target_symbol: Field[str | None] = field(name='target_symbol')
    study_id: Field[str | None] = field(name='study_id')
    evidence: Field[Array[AssociationTableEvidenceStruct]] = field(name='evidence')
    score: Field[float | None] = field(name='score')

__all__ = ['AssociationTable']
