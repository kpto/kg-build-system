"""Reusable nested evidence shape used by association contracts and projections."""

from kg_build_system import CollectionField, Field, Struct, collection_field, field


class EvidenceStruct(Struct):
    """Evidence attached to an association."""
    disease_id: Field[str] = field()
    labels: CollectionField[str] = collection_field()
