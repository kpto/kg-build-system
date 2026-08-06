"""Concrete reference-data contracts for canonical graph entities."""

from kg_build_system import Field, Table, field


class TargetTable(Table):
    target_id: Field[str] = field()
    symbol: Field[str] = field()
    description: Field[str | None] = field()


class DiseaseTable(Table):
    disease_id: Field[str] = field()
    name: Field[str] = field()
    description: Field[str | None] = field()
