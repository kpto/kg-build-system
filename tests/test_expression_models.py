"""Tests for the authoring expression domain models."""

from __future__ import annotations

import unittest

from kg_build_system.expressions.base import field_reference, operation
from kg_build_system.expressions.codec import decode_expression, encode_expression
from kg_build_system.expressions.models import FieldReferenceExpression, LiteralExpression, RowEffect, RowSemantics, Traversal
from kg_build_system.expressions.literals import literal
from kg_build_system.expressions.visitors import rewrite_expression, walk_expression
from kg_build_system.types import ArrayType, INT, NullableType, STR


class ExpressionIRTests(unittest.TestCase):
    def test_literal_inference_and_explicit_nullability(self) -> None:
        self.assertEqual(literal("target").logical_type, STR)
        self.assertEqual(literal([1, None]).logical_type, ArrayType(NullableType(INT)))
        self.assertEqual(literal(None, logical_type=NullableType(STR)).value, None)
        with self.assertRaisesRegex(TypeError, "null literal requires"):
            literal(None)
        with self.assertRaisesRegex(TypeError, "must be int"):
            literal([1, "two"], logical_type=ArrayType(INT))

    def test_field_references_retain_traversal_and_row_information(self) -> None:
        expression = field_reference(
            source="association",
            path=("evidence", "labels"),
            logical_type=STR,
            traversals=(Traversal("array", ("evidence",)), Traversal("array", ("evidence", "labels"))),
            row_semantics=RowSemantics("expand", ("association", "evidence", "labels")),
        )
        self.assertEqual(expression.path, ("evidence", "labels"))
        self.assertEqual(expression.row_semantics.mode, "expand")
        with self.assertRaisesRegex(ValueError, "prefix"):
            field_reference(
                source="association", path=("evidence",), logical_type=STR,
                traversals=(Traversal("struct", ("details",)),),
            )

    def test_operation_parameters_are_deeply_immutable_and_canonical(self) -> None:
        expression = operation(
            "cast", literal(1), logical_type=STR,
            parameters={"z": ["a", {"nested": True}], "sql_type": "TEXT"},
        )
        self.assertEqual(tuple(parameter.name for parameter in expression.parameters), ("sql_type", "z"))
        self.assertIsInstance(expression.parameters[1].value, tuple)

    def test_codec_round_trips_every_node_kind(self) -> None:
        reference = field_reference(
            source="target", path=("id",), logical_type=STR,
            traversals=(Traversal("struct", ("id",)),),
        )
        expression = operation(
            "concat", literal("target::"), reference, logical_type=STR,
            parameters={"separator": ""},
        )
        self.assertEqual(decode_expression(encode_expression(expression)), expression)
        empty_array = literal([], logical_type=ArrayType(INT))
        self.assertEqual(encode_expression(empty_array)["value"], [])
        self.assertEqual(decode_expression(encode_expression(empty_array)), empty_array)

    def test_walk_and_bottom_up_rewrite(self) -> None:
        expression = operation("add", literal(1), literal(2), logical_type=INT)
        self.assertEqual(len(tuple(walk_expression(expression))), 3)

        def replace_two(node: object):
            if isinstance(node, LiteralExpression) and node.value == 2:
                return literal(3)
            return node

        rewritten = rewrite_expression(expression, replace_two)  # type: ignore[arg-type]
        self.assertNotEqual(rewritten, expression)
        self.assertEqual(tuple(walk_expression(rewritten))[-1], literal(3))

    def test_operations_compose_and_share_ordered_row_effects(self) -> None:
        first = operation(
            "expand", literal([1], logical_type=ArrayType(INT)), logical_type=INT,
            row_semantics=RowSemantics("expand", ("input", "values")),
        )
        combined = operation("add", first, first, logical_type=INT)
        self.assertEqual(
            combined.row_semantics.effects,
            (RowEffect("expand", ("input", "values")),),
        )
        filtered = operation(
            "where_present", combined, logical_type=INT,
            row_semantics=RowSemantics("filter"),
        )
        self.assertEqual(
            filtered.row_semantics.effects,
            (RowEffect("expand", ("input", "values")), RowEffect("filter")),
        )
        self.assertEqual(decode_expression(encode_expression(filtered)), filtered)

    def test_invalid_row_semantics_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "stable scope"):
            RowSemantics("expand")
        with self.assertRaisesRegex(ValueError, "only expanding"):
            RowSemantics("filter", ("field",))
        with self.assertRaisesRegex(ValueError, "unknown row-semantics"):
            RowSemantics("invalid")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "upstream"):
            RowSemantics("preserve", upstream=(RowEffect("filter"),))


if __name__ == "__main__":
    unittest.main()
