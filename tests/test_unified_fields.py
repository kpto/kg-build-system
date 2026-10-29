from __future__ import annotations

import unittest
from dataclasses import dataclass

from kg_build_system.annotations.interfaces import Annotation
from kg_build_system.expressions.interfaces import (
    ArraySelection, IntExpression, NullableSelection, StrExpression,
    StructSelection, ValueSelection, field_reference, select_expression,
    value_expression, wrap_expression,
)
from kg_build_system.table.fields import (
    Field, computed_field, declared_fields, field,
)
from kg_build_system.table.models import (
    ComputedStruct, Projection, Struct, Table, TableOptions,
)
from kg_build_system.types.interfaces import (
    Array, ArrayType, INT, NullableType, STR, StructType, normalize_type,
)


@dataclass(frozen=True)
class Indexed(Annotation):
    namespace = "test"
    annotation_id = "indexed"
    unique: bool = False


class EvidenceStruct(Struct):
    label: Field[str] = field()
    labels: Field[Array[str]] = field()


class DetailsStruct(Struct):
    label: Field[str] = field(description="Display label")
    maybe_score: Field[int | None] = field()
    evidence: Field[EvidenceStruct] = field()
    scores: Field[Array[int]] = field()


class InputTable(Table):
    options = TableOptions(name="input")
    targetID: Field[str] = field(annotations=(Indexed(unique=True),))
    options_: Field[str] = field()
    details: Field[DetailsStruct] = field()
    scores: Field[Array[int]] = field()
    evidence: Field[Array[EvidenceStruct]] = field()


class InputShape:
    inherited: Field[int] = field()
    removed: Field[str] = field()


class ExtendedInputTable(InputShape, Table):
    removed = "shadowed"
    renamed: Field[str] = field(name="externalName")


class ComputedRecord(ComputedStruct):
    label = computed_field(value_expression("ready"))
    maybe = computed_field(InputTable.details.extract(lambda value: value.label))


class HoldsComputed(Table):
    record: Field[ComputedRecord] = field()


class NullableDeclared(Table):
    maybe: Field[str | None] = field()
    items: Field[Array[int | None] | None] = field()


class TypedProjection(Projection(InputTable.row_source())):
    label = computed_field(
        InputTable.details.extract(lambda value: value.label)
        .alter_rows().drop_null()
    )
    maybe = computed_field(InputTable.details.extract(lambda value: value.label))
    scores = computed_field(InputTable.scores.alter_rows().drop_null())


class UnifiedFieldTests(unittest.TestCase):
    def test_source_fields_are_always_nullable_on_access(self) -> None:
        for attribute in ("targetID", "details", "scores", "evidence"):
            with self.subTest(attribute=attribute):
                self.assertIsInstance(getattr(InputTable, attribute), NullableSelection)

        self.assertEqual(InputTable.targetID.logical_type, NullableType(STR))
        self.assertEqual(
            InputTable.scores.logical_type, NullableType(ArrayType(INT)),
        )

    def test_nullable_array_access_requires_the_row_gate(self) -> None:
        scores = InputTable.scores
        self.assertIsInstance(scores, NullableSelection)
        self.assertFalse(hasattr(scores, "expand"))

        expanded = scores.alter_rows().drop_null().expand()
        self.assertIsInstance(expanded, ValueSelection)
        self.assertIsInstance(expanded.expression, IntExpression)

    def test_drop_null_refines_a_source_selection(self) -> None:
        narrowed = InputTable.targetID.alter_rows().drop_null()
        self.assertIsInstance(narrowed, ValueSelection)
        self.assertNotIsInstance(narrowed, NullableSelection)
        self.assertEqual(narrowed.logical_type, STR)
        self.assertIsInstance(narrowed.expression, StrExpression)

    def test_struct_source_members_are_nullable_inside_extract(self) -> None:
        label = InputTable.details.extract(lambda value: value.label)
        self.assertIsInstance(label, NullableSelection)
        self.assertEqual(label.logical_type, NullableType(STR))
        self.assertEqual(label.expression.model.path, ("details", "label"))  # type: ignore[attr-defined]

        narrowed = (
            InputTable.details.alter_rows().drop_null()
            .extract(lambda value: value.label)
            .alter_rows().drop_null()
        )
        self.assertIsInstance(narrowed, ValueSelection)
        self.assertIsInstance(narrowed.expression, StrExpression)

    def test_nested_source_member_propagation(self) -> None:
        evidence = InputTable.details.extract(lambda value: value.evidence)
        self.assertIsInstance(evidence, NullableSelection)
        nested_label = evidence.extract(lambda value: value.label)
        self.assertIsInstance(nested_label, NullableSelection)
        self.assertEqual(
            nested_label.expression.model.path,  # type: ignore[attr-defined]
            ("details", "evidence", "label"),
        )

    def test_computed_struct_members_stay_typed_and_inherit_parent_nullability(self) -> None:
        self.assertIsInstance(ComputedRecord.label, ValueSelection)
        self.assertNotIsInstance(ComputedRecord.label, NullableSelection)
        self.assertIsInstance(ComputedRecord.maybe, NullableSelection)

        computed_type = normalize_type(ComputedRecord)
        self.assertEqual(
            computed_type,
            StructType(ComputedRecord.__module__, ComputedRecord.__qualname__),
        )
        present = select_expression(wrap_expression(field_reference(
            source="input", path=("record",), logical_type=computed_type,
        )))
        self.assertIsInstance(present, StructSelection)
        self.assertIsInstance(present.extract(lambda value: value.label), ValueSelection)
        self.assertIsInstance(present.extract(lambda value: value.maybe), NullableSelection)

        absent = select_expression(wrap_expression(field_reference(
            source="input", path=("record",), logical_type=NullableType(computed_type),
        )))
        self.assertIsInstance(absent.extract(lambda value: value.label), NullableSelection)

    def test_computed_struct_is_a_value_type_and_a_table_is_not(self) -> None:
        self.assertIsInstance(HoldsComputed.record, NullableSelection)
        with self.assertRaisesRegex(TypeError, "row source"):
            normalize_type(InputTable)
        with self.assertRaisesRegex(TypeError, "row source"):
            normalize_type(TypedProjection)

    def test_projection_fields_read_the_materialised_output(self) -> None:
        self.assertIsInstance(TypedProjection.label, ValueSelection)
        self.assertNotIsInstance(TypedProjection.label, NullableSelection)
        self.assertEqual(TypedProjection.label.logical_type, STR)
        self.assertEqual(
            TypedProjection.label.expression.model.source,  # type: ignore[attr-defined]
            TypedProjection._projection_name,
        )
        self.assertIsInstance(TypedProjection.maybe, NullableSelection)
        self.assertIsInstance(TypedProjection.scores, ArraySelection)
        self.assertIsNotNone(declared_fields(TypedProjection)["label"].expression)

    def test_metadata_naming_annotations_and_escape_are_preserved(self) -> None:
        fields = declared_fields(InputTable)
        self.assertEqual(fields["targetID"].metadata.name, "target_id")
        self.assertEqual(fields["options_"].metadata.name, "options")
        self.assertEqual(fields["targetID"].metadata.annotations, (Indexed(unique=True),))
        self.assertEqual(declared_fields(DetailsStruct)["label"].metadata.description, "Display label")

    def test_inheritance_and_validation(self) -> None:
        fields = declared_fields(ExtendedInputTable)
        self.assertIn("inherited", fields)
        self.assertNotIn("removed", fields)
        self.assertEqual(fields["renamed"].metadata.name, "externalName")
        with self.assertRaisesRegex(TypeError, r"Field\[T\]"):
            class MissingAnnotationTable(Table):
                value = field()
        with self.assertRaisesRegex(TypeError, "share external name"):
            class DuplicateTable(Table):
                first: Field[str] = field(name="same")
                second: Field[str] = field(name="same")

    def test_owner_kind_validates_the_constructor(self) -> None:
        with self.assertRaisesRegex(TypeError, "computed_field"):
            class ComputedTable(Table):
                value: Field[str] = computed_field(value_expression("x"))

        with self.assertRaisesRegex(TypeError, "computed_field"):
            class ComputedStructSource(Struct):
                value: Field[str] = computed_field(value_expression("x"))

        with self.assertRaisesRegex(TypeError, r"field\(\)"):
            class DeclaredProjection(Projection(InputTable.row_source())):
                value = field()

        with self.assertRaisesRegex(TypeError, "computed_field"):
            class DeclaredComputed(ComputedStruct):
                value: Field[str] = field()

    def test_declared_source_field_has_no_expression(self) -> None:
        self.assertIsNone(declared_fields(InputTable)["targetID"].expression)

    def test_a_top_level_nullable_declaration_is_stripped(self) -> None:
        fields = declared_fields(NullableDeclared)
        self.assertEqual(fields["maybe"]._logical_type(NullableDeclared), STR)
        self.assertEqual(
            fields["items"]._logical_type(NullableDeclared),
            ArrayType(NullableType(INT)),
            "only the outer nullability is stripped; item nullability is a value fact",
        )
        self.assertIsInstance(NullableDeclared.maybe, NullableSelection)


if __name__ == "__main__":
    unittest.main()
