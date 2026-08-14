from __future__ import annotations

import unittest
from dataclasses import dataclass

from kg_build_system.annotations import Annotation
from kg_build_system.expressions import (
    ArrayValueExpression,
    IntValueExpression,
    NullableValueExpression,
    PickedField,
    StrValueExpression,
    StructNullableValueExpression,
    StructValueExpression,
)
from kg_build_system.table.fields import Field, declared_fields, field
from kg_build_system.table.models import Table, TableOptions
from kg_build_system.types import Array, INT, NullableType, Struct


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
    evidence: Field[EvidenceStruct | None] = field()
    scores: Field[Array[int] | None] = field()


class InputTable(Table):
    options = TableOptions(name="input")
    targetID: Field[str] = field(annotations=(Indexed(unique=True),))
    options_: Field[str] = field()
    details: Field[DetailsStruct | None] = field()
    scores: Field[Array[int]] = field()
    evidence: Field[Array[EvidenceStruct]] = field()


class InputShape:
    inherited: Field[int] = field()
    removed: Field[str] = field()


class ExtendedInputTable(InputShape, Table):
    removed = "shadowed"
    renamed: Field[str] = field(name="externalName")


class UnifiedFieldTests(unittest.TestCase):
    def test_table_fields_are_specific_typed_expressions(self) -> None:
        self.assertIsInstance(InputTable.targetID, StrValueExpression)
        self.assertEqual(InputTable.targetID.expression.source, "input")
        self.assertEqual(InputTable.targetID.expression.path, ("target_id",))
        self.assertIsInstance(InputTable.scores, ArrayValueExpression)
        self.assertIsInstance(InputTable.scores.each(), IntValueExpression)
        self.assertIsInstance(InputTable.details, StructNullableValueExpression)

    def test_struct_fields_are_typed_pick_tokens(self) -> None:
        label = object.__new__(DetailsStruct).label
        score = object.__new__(DetailsStruct).maybe_score
        self.assertIsInstance(label, PickedField)
        self.assertEqual(label.name, "label")
        self.assertEqual(score.logical_type, NullableType(INT))

        selected = InputTable.details.pick(lambda value: value.label)
        self.assertIsInstance(selected, NullableValueExpression)
        self.assertIsInstance(selected.expression, type(InputTable.targetID.expression))
        self.assertEqual(selected.expression.path, ("details", "label"))

        nested = InputTable.details.pick(lambda value: value.evidence)
        self.assertIsInstance(nested, StructNullableValueExpression)
        nested_label = nested.pick(lambda value: value.label)
        self.assertIsInstance(nested_label, NullableValueExpression)
        self.assertEqual(nested_label.expression.path, ("details", "evidence", "label"))

    def test_nested_array_expansion_retains_complete_row_context(self) -> None:
        evidence = InputTable.evidence.each()
        self.assertIsInstance(evidence, StructValueExpression)
        labels = evidence.pick(lambda value: value.labels).each().append("!")
        effects = labels.expression.row_semantics.effects
        self.assertEqual(len(effects), 2)
        self.assertTrue(all(effect.mode == "expand" for effect in effects))
        self.assertEqual(effects[0].scope, ("input", "evidence"))

    def test_struct_selector_rejects_a_field_from_another_declaration(self) -> None:
        with self.assertRaisesRegex(TypeError, "input declaration"):
            InputTable.details.pick(lambda _value: object.__new__(EvidenceStruct).label)

    def test_metadata_naming_annotations_and_escape_are_preserved(self) -> None:
        fields = declared_fields(InputTable)
        self.assertEqual(fields["targetID"].metadata.name, "target_id")
        self.assertEqual(fields["options_"].metadata.name, "options")
        self.assertEqual(fields["details"].metadata.description, None)
        self.assertEqual(fields["targetID"].metadata.annotations, (Indexed(unique=True),))
        self.assertEqual(declared_fields(DetailsStruct)["label"].metadata.description, "Display label")

    def test_inheritance_uses_python_shadowing_and_explicit_names(self) -> None:
        fields = declared_fields(ExtendedInputTable)
        self.assertIn("inherited", fields)
        self.assertNotIn("removed", fields)
        self.assertEqual(fields["renamed"].metadata.name, "externalName")

    def test_invalid_annotations_and_duplicate_external_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, r"Field\[T\]"):
            class MissingAnnotationTable(Table):
                value = field()

        with self.assertRaisesRegex(TypeError, "share external name"):
            class DuplicateTable(Table):
                first: Field[str] = field(name="same")
                second: Field[str] = field(name="same")


if __name__ == "__main__":
    unittest.main()
