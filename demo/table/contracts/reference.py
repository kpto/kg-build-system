"""Concrete reference-data contracts for canonical graph entities."""

from kg_build_system import Field, field, table


@table()
class TargetTable:
    target_id: Field[str] = field()
    symbol: Field[str] = field()


@table()
class DiseaseTable:
    disease_id: Field[str] = field()
    name: Field[str] = field()
