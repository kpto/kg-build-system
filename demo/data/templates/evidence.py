"""Reusable nested evidence shape used by association contracts and projections."""

from kg_build_system import Field, field, struct


@struct(name="evidence", description="Evidence attached to an association.")
class Evidence:
    disease_id: Field[str] = field(name="disease_id")
    labels: Field[list[str]] = field(name="labels")
