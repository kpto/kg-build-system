"""An unnested row source keeps its surviving fields on the scanned relation."""
from __future__ import annotations

import json
import unittest

from kg_build_system import (
    Array,
    Claim,
    Contract,
    Definition,
    DerivedRelation,
    DerivedRelationOptions,
    Field,
    Meaning,
    Omitted,
    Purpose,
    SourceRelation,
    Struct,
    computed_field,
    field,
)
from kg_build_system.distribution.languages.data.service.internal import (
    data_to_document,
    plan_shape_source_name,
    transcribe_data,
)
from .support import TestEstate


class Item(Struct):
    value: Field[float] = field(meaning=Omitted)


class Parent(SourceRelation[TestEstate]):
    item_id: Field[str] = field(meaning=Omitted)
    items: Field[Array[Item | None]] = field(meaning=Omitted)


items = Parent.row_source().unnest(lambda row: row.items)


class ParentItem(DerivedRelation(items)):
    options = DerivedRelationOptions(
        name="parent_item",
        contract=Contract(
            definition=Definition(
                grain="one row per item of a parent",
                identity=("item_id", "value"),
            ),
            meaning=Meaning(purpose=Purpose("Read one item per parent.")),
        ),
    )

    item_id = computed_field(items.shape.item_id.alter_rows().drop_null(), meaning=Omitted)
    value = computed_field(items.shape.items.extract(lambda item: item.value), meaning=Omitted)


class UnnestProvenanceTests(unittest.TestCase):
    def test_the_unnested_shape_names_the_scanned_relation(self) -> None:
        self.assertEqual(plan_shape_source_name(items.plan_dto), "parent")

    def test_outputs_reference_the_scanned_relation_not_a_digest(self) -> None:
        document = json.dumps(data_to_document(transcribe_data((ParentItem,))))
        self.assertNotIn("derived:", document)
        self.assertIn('"parent.item_id"', document)


if __name__ == "__main__":
    unittest.main()
