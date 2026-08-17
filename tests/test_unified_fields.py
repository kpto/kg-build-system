from __future__ import annotations

import unittest
from dataclasses import dataclass

from kg_build_system.annotations import Annotation
from kg_build_system.expressions import (
    ArrayExpression, ArraySelection, IntExpression, NullableSelection,
    StrExpression, StructSelection, ValueSelection,
)
from kg_build_system.table.fields import Field, declared_fields, field
from kg_build_system.table.models import Table, TableOptions
from kg_build_system.types import Array, NullableType, Struct


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
    def test_table_fields_are_shape_specialized_selections(self) -> None:
        self.assertIsInstance(InputTable.targetID, ValueSelection)
        self.assertIsInstance(InputTable.targetID.expression, StrExpression)
        self.assertEqual(InputTable.targetID.expression.model.source, "input")  # type: ignore[attr-defined]
        self.assertEqual(InputTable.targetID.expression.model.path, ("target_id",))  # type: ignore[attr-defined]
        self.assertIsInstance(InputTable.scores, ArraySelection)
        self.assertIsInstance(InputTable.scores.expression, ArrayExpression)
        self.assertIsInstance(InputTable.scores.expand().expression, IntExpression)
        self.assertIsInstance(InputTable.details, NullableSelection)

    def test_struct_fields_are_temporary_selections_consumed_by_pick(self) -> None:
        label = object.__new__(DetailsStruct).label
        score = object.__new__(DetailsStruct).maybe_score
        self.assertIsInstance(label, ValueSelection)
        self.assertIsInstance(score, NullableSelection)
        self.assertIsInstance(score.logical_type, NullableType)

        selected = InputTable.details.pick(lambda value: value.label)
        self.assertIsInstance(selected, NullableSelection)
        self.assertEqual(selected.expression.model.path, ("details", "label"))  # type: ignore[attr-defined]

        nested = InputTable.details.pick(lambda value: value.evidence)
        self.assertIsInstance(nested, NullableSelection)
        nested_label = nested.pick(lambda value: value.label)
        self.assertEqual(nested_label.expression.model.path, ("details", "evidence", "label"))  # type: ignore[attr-defined]

    def test_nested_expansion_retains_complete_row_context(self) -> None:
        evidence = InputTable.evidence.expand()
        self.assertIsInstance(evidence, StructSelection)
        labels = evidence.pick(lambda value: value.labels).expand().expression.append("!")
        effects = labels.model.row_semantics.effects
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


if __name__ == "__main__":
    unittest.main()
