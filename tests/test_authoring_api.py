from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.binding import (
    NodeValues,
    node_binding,
)
from kg_build_system.distribution.languages.data import (
    Field,
    Projection,
    Struct,
    Table,
    computed_field,
    field,
)
from kg_build_system.distribution.languages.expressions import (
    NullableSelection,
    Selection,
)
from kg_build_system.distribution.languages.topology import (
    Node,
    NodeOptions,
    PropertySlot,
    property,
)
from kg_build_system.kernel import Array, Nullable, NullableType, StructType
from tests.distribution.support import TestEstate


class Address(Struct):
    city: Field[str] = field(name="city")
    postcodes: Field[Array[str]] = field(name="postcodes")


class Detail(Struct):
    label: Field[str] = field(name="label")
    address: Field[Address] = field(name="address")


class Source(Table[TestEstate]):
    id: Field[str] = field(name="id")
    detail: Field[Detail] = field(name="detail")
    details: Field[Array[Detail]] = field(name="details")
    tags: Field[Array[str]] = field(name="tags")
    labels: Field[Array[Nullable[str]]] = field(name="labels")


source_tags = Source.tags.alter_rows().drop_null()
source_details = Source.details.alter_rows().drop_null()


class SourceProjection(Projection(Source.row_source())):
    ident = computed_field(Source.id.alter_rows().drop_null())
    nullable_ident = computed_field(Source.id)


class SourceNode(Node):
    options = NodeOptions(name="source_node")
    label: PropertySlot[str] = property()


class AuthoringApiTests(unittest.TestCase):
    def test_source_access_is_nullable_and_computed_access_is_typed(self) -> None:
        self.assertIsInstance(Source.id, Selection)
        self.assertIsInstance(Source.id.logical_type, NullableType)
        self.assertEqual(SourceProjection.ident.logical_type.name, "str")
        self.assertIsInstance(Source.detail.logical_type.value, StructType)
        self.assertEqual(SourceProjection.ident.logical_type.name, "str")
        self.assertFalse(
            isinstance(SourceProjection.ident.logical_type, NullableType)
        )
        self.assertIsInstance(
            SourceProjection.nullable_ident.logical_type, NullableType
        )

    def test_extract_composes_parent_presence_and_member_owner_kind(self) -> None:
        source_member = Source.detail.extract(lambda value: value.label)
        self.assertIsInstance(source_member.logical_type, NullableType)
        nested = Source.detail.extract(lambda value: value.address)
        self.assertIsInstance(nested.logical_type, NullableType)
        self.assertIsInstance(
            nested.extract(lambda value: value.city).logical_type,
            NullableType,
        )
        present = source_details.alter_rows().expand()
        self.assertIsInstance(
            present.extract(lambda value: value.label).logical_type,
            NullableType,
        )

    def test_row_effects_are_only_reached_through_alter_rows(self) -> None:
        for selection in (Source.id, Source.detail, Source.tags, Source.details):
            for method in ("drop_null", "drop_if", "expand"):
                with self.subTest(selection=selection, method=method):
                    self.assertFalse(hasattr(selection, method))

    def test_handles_expose_only_valid_effects(self) -> None:
        self.assertFalse(hasattr(Source.id.alter_rows(), "expand"))
        self.assertFalse(hasattr(SourceProjection.ident.alter_rows(), "drop_null"))
        self.assertFalse(hasattr(Source.detail.alter_rows(), "expand"))
        self.assertTrue(hasattr(Source.tags.alter_rows(), "expand"))
        self.assertTrue(hasattr(source_tags.alter_rows(), "expand"))
        self.assertFalse(hasattr(source_tags.alter_rows(), "drop_null"))
        self.assertTrue(hasattr(Source.id.alter_rows(), "drop_if"))
        self.assertTrue(hasattr(Source.id.alter_rows(), "drop_null"))

    def test_a_row_effect_handle_is_one_shot(self) -> None:
        handle = Source.id.alter_rows()
        self.assertIsNotNone(handle.drop_null())
        with self.assertRaisesRegex(TypeError, "already consumed"):
            handle.drop_null()

    def test_drop_and_expand_shapes(self) -> None:
        dropped = Source.id.alter_rows().drop_null()
        self.assertFalse(isinstance(dropped.logical_type, NullableType))
        expanded = source_details.alter_rows().expand()
        self.assertEqual(expanded.logical_type, Source.details.logical_type.value.item)

    def test_source_field_rejects_a_nullable_annotation(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be T, not T"):
            class Bad(Table[TestEstate]):
                value: Field[str | None] = field(name="value")

    def test_projection_requires_a_source_and_rejects_class_sugar(self) -> None:
        with self.assertRaisesRegex(TypeError, "requires a row source"):
            Projection()
        with self.assertRaisesRegex(TypeError, "requires a row source"):
            class BadProjection(Projection):
                value = computed_field(Source.id)

    def test_computed_field_is_the_projection_output_constructor(self) -> None:
        self.assertEqual(
            SourceProjection.ident.logical_type.name,
            Source.id.alter_rows().drop_null().logical_type.name,
        )

    def test_binding_rows_accept_a_row_source_not_the_declaration_class(self) -> None:
        seen: list[object] = []

        def bind(row: Source) -> NodeValues[SourceNode, str]:
            seen.append(row)
            return NodeValues(
                build_key=row.id.alter_rows().drop_null(),
                properties=SourceNode(label=row.id.alter_rows().drop_null()),
            )

        binding = node_binding(
            target=SourceNode, rows=Source.row_source(), bind=bind,
        )
        self.assertTrue(binding.rows is not None)
        self.assertEqual(len(seen), 1)
        self.assertIsInstance(seen[0], Source)
        with self.assertRaisesRegex(TypeError, "row source value"):
            node_binding(target=SourceNode, rows=Source, bind=bind)

    def test_no_expression_escape_hatch_or_old_names(self) -> None:
        for name in (".expression", ".value", ".model", "require_expression"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(Source.id, name.strip(".")))
        self.assertFalse(hasattr(Source, "projection_base"))
        self.assertFalse(hasattr(SourceProjection, "projection_base"))
        self.assertFalse(hasattr(Source.tags, "distinct"))
        self.assertFalse(hasattr(Source.tags, "join"))
        self.assertFalse(hasattr(Source.id, "where_present"))
        self.assertFalse(hasattr(Source.id, "where_if"))
        self.assertFalse(hasattr(Source.id, "pick"))
        self.assertTrue(hasattr(Source.tags, "concat"))

    def test_selection_is_the_only_authoring_type(self) -> None:
        import kg_build_system.distribution.languages.expressions as expressions

        self.assertIn("Selection", expressions.__all__)
        self.assertIn("NullableSelection", expressions.__all__)
        for removed in (
            "ValueSelection", "ArraySelection", "StructSelection",
            "ValueExpression", "ValueInput", "as_expression",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, expressions.__all__)


if __name__ == "__main__":
    unittest.main()
