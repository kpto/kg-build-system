from kg_build_system import Field, Table, TableOptions, field


class DiseaseTable(Table):
    options = TableOptions(name='disease')
    disease_id: Field[str | None] = field(name='disease_id')
    name: Field[str | None] = field(name='name')
    description: Field[str | None] = field(name='description')

__all__ = ['DiseaseTable']
