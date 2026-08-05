"""Reusable nested evidence shape used by association contracts and projections."""

from kg_build_system import Field, field, struct


@struct(description="Evidence attached to an association.")
class EvidenceStruct:
    disease_id: Field[str] = field()
    labels: Field[list[str]] = field()
