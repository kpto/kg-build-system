from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.expressions import (
    NullableSelection,
    ValueSelection,
)
from kg_build_system.distribution.languages.data import (
    Field,
    Projection,
    Struct,
    Table,
    field,
    projection_field,
)
from kg_build_system.kernel import Array, Nullable
from tests.distribution.support import TestEstate


class Detail(Struct):
    label: Field[str | None] = field(name="label")


class Source(Table[TestEstate]):
    id: Field[str] = field(name="id")
    detail: Field[Detail | None] = field(name="detail")
    details: Field[Array[Detail] | None] = field(name="details")
    tags: Field[Array[str]] = field(name="tags")
    labels: Field[Array[Nullable[str]]] = field(name="labels")


class SourceProjection(Projection):
    ident = projection_field(Source.id)


class AuthoringApiTests(unittest.TestCase):
    def test_source_access_follows_the_declaration(self) -> None:
        self.assertIsInstance(Source.id, ValueSelection)
        self.assertIsInstance(Source.detail, NullableSelection)

    def test_selection_operations_compose(self) -> None:
        selected = (
            Source.details
            .alter_rows().drop_null()
            .drop_null_items()
            .alter_rows().expand()
            .extract(lambda item: item.label)
            .alter_rows().drop_null()
        )
        self.assertIsInstance(selected, ValueSelection)
        self.assertEqual(
            getattr(selected.expression.model, "operator", None),
            "drop_null",
        )

    def test_row_effects_are_only_reached_through_alter_rows(self) -> None:
        for selection in (Source.id, Source.detail, Source.tags, Source.details):
            for method in ("drop_null", "drop_if", "expand"):
                with self.subTest(selection=selection, method=method):
                    self.assertFalse(hasattr(selection, method))

    def test_only_array_handles_expose_expand(self) -> None:
        self.assertFalse(hasattr(Source.id.alter_rows(), "expand"))
        self.assertFalse(hasattr(Source.detail.alter_rows(), "expand"))
        self.assertTrue(hasattr(Source.tags.alter_rows(), "expand"))
        self.assertTrue(hasattr(Source.details.alter_rows(), "expand"))

    def test_a_row_effect_handle_is_one_shot(self) -> None:
        selection = Source.id
        handle = selection.alter_rows()
        self.assertIs(handle.drop_null(), selection)
        with self.assertRaises(RuntimeError):
            handle.drop_null()

    def test_drop_if_returns_the_same_selection_type(self) -> None:
        selected = Source.id.alter_rows().drop_if(
            lambda value: value.expression.equals("a")
        )
        self.assertIsInstance(selected, ValueSelection)

    def test_concat_rejects_nullable_items(self) -> None:
        with self.assertRaisesRegex(TypeError, "array of non-null strings"):
            Source.labels.concat(",")

    def test_unique_is_the_only_selection_level_distinct_name(self) -> None:
        self.assertFalse(hasattr(Source.tags, "distinct"))
        self.assertFalse(hasattr(Source.tags, "join"))
        self.assertEqual(
            getattr(Source.tags.unique().expression.model, "operator", None),
            "distinct",
        )

    def test_an_unpinned_projection_uses_projection_field(self) -> None:
        self.assertEqual(SourceProjection.ident.logical_type, Source.id.logical_type)


if __name__ == "__main__":
    unittest.main()
