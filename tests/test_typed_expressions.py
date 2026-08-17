from __future__ import annotations

import unittest

from kg_build_system import Field, Struct, field
from kg_build_system.expressions import (
    ArrayExpression, ArraySelection, BoolExpression, FloatExpression,
    IntExpression, NullableExpression, NullableSelection, StrExpression,
    StructExpression, StructSelection, ValueSelection, select_expression,
    value_expression, wrap_expression,
)
from kg_build_system.expressions.base import field_reference
from kg_build_system.expressions.models import FieldReferenceExpression, OperationExpression
from kg_build_system.types import Array, INT, NullableType, STR, normalize_type


class DetailsStruct(Struct):
    label: Field[str] = field()
    maybe_score: Field[int | None] = field()


class TypedExpressionTests(unittest.TestCase):
    def test_factory_selects_specific_bindable_expression_families(self) -> None:
        self.assertIsInstance(value_expression(True), BoolExpression)
        self.assertIsInstance(value_expression(1), IntExpression)
        self.assertIsInstance(value_expression(1.5), FloatExpression)
        self.assertIsInstance(value_expression("name"), StrExpression)
        nullable = value_expression(None, logical_type=NullableType(STR))
        self.assertIsInstance(nullable, NullableExpression)
        self.assertFalse(hasattr(nullable, "default_to"))

    def test_specialized_calculations_retain_their_family(self) -> None:
        self.assertIsInstance(value_expression(1).add(2).sub(1), IntExpression)
        self.assertIsInstance(value_expression(1.5).add(1), FloatExpression)
        self.assertIsInstance(value_expression("target").prepend("[").append("]"), StrExpression)
        self.assertIsInstance(value_expression(True).not_().and_(True), BoolExpression)

    def test_null_policy_belongs_to_selections(self) -> None:
        selection = select_expression(wrap_expression(field_reference(
            source="input", path=("score",), logical_type=NullableType(INT),
        )))
        self.assertIsInstance(selection, NullableSelection)
        defaulted = selection.default_to(0)
        narrowed = selection.where_present()
        self.assertIsInstance(defaulted, ValueSelection)
        self.assertIsInstance(defaulted.expression, IntExpression)
        self.assertIsInstance(narrowed.expression, IntExpression)
        self.assertEqual(narrowed.expression.model.row_semantics.mode, "filter")
        self.assertIsInstance(narrowed.expression.model, OperationExpression)
        self.assertEqual(narrowed.expression.model.operator, "where_present")

    def test_array_expansion_preserves_item_nullability_and_scope(self) -> None:
        values = select_expression(wrap_expression(field_reference(
            source="input", path=("values",), logical_type=normalize_type(Array[int | None]),
        )))
        self.assertIsInstance(values, ArraySelection)
        self.assertIsInstance(values.expression, ArrayExpression)
        item = values.expand()
        self.assertIsInstance(item, NullableSelection)
        self.assertIsInstance(item.expression, NullableExpression)
        self.assertEqual(item.logical_type, NullableType(INT))
        self.assertEqual(item.expression.model.row_semantics.scope, ("input", "values"))

    def test_struct_pick_returns_selections_and_propagates_parent_nullability(self) -> None:
        required = select_expression(wrap_expression(field_reference(
            source="input", path=("details",), logical_type=normalize_type(DetailsStruct),
        )))
        self.assertIsInstance(required, StructSelection)
        self.assertIsInstance(required.expression, StructExpression)
        label = required.pick(lambda item: item.label)
        self.assertIsInstance(label, ValueSelection)
        self.assertIsInstance(label.expression, StrExpression)
        self.assertIsInstance(required.pick(lambda item: item.maybe_score), NullableSelection)

        optional = select_expression(wrap_expression(field_reference(
            source="input", path=("details",), logical_type=normalize_type(DetailsStruct | None),
        )))
        selected = optional.pick(lambda item: item.label)
        self.assertIsInstance(selected, NullableSelection)
        self.assertEqual(selected.logical_type, NullableType(STR))
        self.assertIsInstance(selected.expression.model, FieldReferenceExpression)
        self.assertEqual(selected.expression.model.path, ("details", "label"))


if __name__ == "__main__":
    unittest.main()
