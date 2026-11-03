from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.expressions import (
    NullableSelection,
    ValueSelection,
)
from kg_build_system.distribution.languages.table import (
    Field,
    Projection,
    Struct,
    Table,
    field,
    projection_field,
)
from kg_build_system.kernel import Array


class Detail(Struct):
    label: Field[str | None] = field(name="label")


class Source(Table):
    id: Field[str] = field(name="id")
    detail: Field[Detail | None] = field(name="detail")
    details: Field[Array[Detail] | None] = field(name="details")


class OldProjection(Projection):
    ident = projection_field(Source.id)


class OldAuthoringTests(unittest.TestCase):
    def test_source_access_follows_the_declaration(self) -> None:
        self.assertIsInstance(Source.id, ValueSelection)
        self.assertIsInstance(Source.detail, NullableSelection)

    def test_old_selection_spellings_compose(self) -> None:
        selected = (
            Source.details
            .where_present()
            .drop_null_items()
            .expand()
            .pick(lambda item: item.label)
            .where_present()
        )
        self.assertIsInstance(selected, ValueSelection)
        self.assertEqual(
            getattr(selected.expression.model, "operator", None),
            "where_present",
        )

    def test_an_unpinned_projection_uses_projection_field(self) -> None:
        self.assertEqual(OldProjection.ident.logical_type, Source.id.logical_type)


if __name__ == "__main__":
    unittest.main()
