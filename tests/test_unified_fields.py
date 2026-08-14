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
)
from kg_build_system.table.fields import Field, declared_fields, field
from kg_build_system.table.models import Table, TableOptions
from kg_build_system.types import Array, INT, NullableType, Struct


@dataclass(frozen=True)
class Indexed(Annotation):
    namespace = "test"
    annotation_id = "indexed"
    unique: bool = False


class DetailsStruct(Struct):
    label: Field[str] = field(description="Display label")
    maybe_score: Field[int | None] = field()


class InputTable(Table):
    options = TableOptions(name="input")
    targetID: Field[str] = field(annotations=(Indexed(unique=True),))
    options_: Field[str] = field()
    details: Field[DetailsStruct | None] = field()
    scores: Field[Array[int]] = field()


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
        class MissingAnnotationTable(Table):
            value = field()

        with self.assertRaisesRegex(TypeError, r"Field\[T\]"):
            declared_fields(MissingAnnotationTable)

        class DuplicateTable(Table):
            first: Field[str] = field(name="same")
            second: Field[str] = field(name="same")

        with self.assertRaisesRegex(TypeError, "share external name"):
            declared_fields(DuplicateTable)


if __name__ == "__main__":
    unittest.main()
