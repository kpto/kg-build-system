"""Concrete reference-data contracts for canonical graph entities."""

from kg_build_system import Field, field, table


@table(name="target")
class TargetReference:
    target_id: Field[str] = field(name="target_id")
    symbol: Field[str] = field(name="symbol")


@table(name="disease")
class DiseaseReference:
    disease_id: Field[str] = field(name="disease_id")
    name: Field[str] = field(name="name")
