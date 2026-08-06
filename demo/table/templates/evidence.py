"""Reusable nested evidence shape used by association contracts and projections."""

from kg_build_system import Field, Struct, field


class EvidenceStruct(Struct):
    """Evidence attached to an association."""
    disease_id: Field[str] = field()
    labels: Field[list[str]] = field()
