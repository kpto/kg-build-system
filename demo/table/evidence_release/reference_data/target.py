from kg_build_system import Field, Table, TableOptions, field


class TargetTable(Table):
    options = TableOptions(name='target')
    target_id: Field[str | None] = field(name='target_id')
    symbol: Field[str | None] = field(name='symbol')
    description: Field[str | None] = field(name='description')

__all__ = ['TargetTable']
