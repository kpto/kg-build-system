from kg_build_system import Field, Struct, Table, TableOptions, field


class StudyTableDetailsStruct(Struct):
    name: Field[str] = field(name='name')
    description: Field[str | None] = field(name='description')


class StudyTable(Table):
    options = TableOptions(name='study')
    id: Field[str | None] = field(name='id')
    details: Field[StudyTableDetailsStruct] = field(name='details')

__all__ = ['StudyTable']
