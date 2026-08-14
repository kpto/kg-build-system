from __future__ import annotations

import unittest

from kg_build_system.expressions import (
    ArrayNullableValueExpression,
    ArrayValueExpression,
    BoolValueExpression,
    FloatValueExpression,
    IntValueExpression,
    NullableValueExpression,
    PickedField,
    StrValueExpression,
    StructNullableValueExpression,
    StructValueExpression,
    value_expression,
    wrap_expression,
)
from kg_build_system.expressions.base import field_reference
from kg_build_system.expressions.ir import OperationExpression
from kg_build_system.types import Array, INT, NullableType, STR, Struct, normalize_type


class DetailsStruct(Struct):
    label = PickedField("label", STR)
    maybe_score = PickedField("maybe_score", NullableType(INT))


class TypedExpressionTests(unittest.TestCase):
    def test_factory_selects_specific_scalar_and_nullable_families(self) -> None:
        self.assertIsInstance(value_expression(True), BoolValueExpression)
        self.assertIsInstance(value_expression(1), IntValueExpression)
        self.assertIsInstance(value_expression(1.5), FloatValueExpression)
        self.assertIsInstance(value_expression("name"), StrValueExpression)
        nullable = value_expression(None, logical_type=NullableType(STR))
        self.assertIsInstance(nullable, NullableValueExpression)
        self.assertIsInstance(nullable.or_else("unknown"), StrValueExpression)  # type: ignore[attr-defined]

    def test_specialized_operations_retain_their_family(self) -> None:
        integer = value_expression(1)
        floating = value_expression(1.5)
        text = value_expression("target")
        flag = value_expression(True)
        self.assertIsInstance(integer.add(2).sub(1), IntValueExpression)  # type: ignore[attr-defined]
        self.assertIsInstance(floating.add(1), FloatValueExpression)  # type: ignore[attr-defined]
        self.assertIsInstance(text.prepend("[").append("]"), StrValueExpression)  # type: ignore[attr-defined]
        self.assertIsInstance(flag.not_().and_(True), BoolValueExpression)  # type: ignore[attr-defined]

    def test_operations_reject_incompatible_inputs(self) -> None:
        integer = value_expression(1)
        with self.assertRaisesRegex(TypeError, "must be int"):
            integer.add("two")  # type: ignore[attr-defined, arg-type]
        with self.assertRaisesRegex(TypeError, "expected"):
            integer.add(value_expression(2.0))  # type: ignore[attr-defined, arg-type]

    def test_null_narrowing_is_explicit_in_ir(self) -> None:
        source = wrap_expression(
            field_reference(source="input", path=("score",), logical_type=NullableType(INT))
        )
        narrowed = source.when_present()  # type: ignore[attr-defined]
        self.assertIsInstance(narrowed, IntValueExpression)
        self.assertEqual(narrowed.expression.row_semantics.mode, "filter")
        self.assertEqual(narrowed.expression.operator, "when_present")  # type: ignore[attr-defined]

    def test_array_each_preserves_item_nullability_and_stable_scope(self) -> None:
        values = wrap_expression(
            field_reference(
                source="input",
                path=("values",),
                logical_type=normalize_type(Array[int | None]),
            )
        )
        self.assertIsInstance(values, ArrayValueExpression)
        item = values.each()  # type: ignore[attr-defined]
        self.assertIsInstance(item, NullableValueExpression)
        self.assertEqual(item.logical_type, NullableType(INT))
        self.assertEqual(item.expression.row_semantics.scope, ("input", "values"))

        nullable_array = wrap_expression(
            field_reference(
                source="input",
                path=("optional_values",),
                logical_type=normalize_type(Array[int] | None),
            )
        )
        self.assertIsInstance(nullable_array, ArrayNullableValueExpression)
        self.assertIsInstance(nullable_array.each(), IntValueExpression)  # type: ignore[attr-defined]

    def test_struct_pick_propagates_only_parent_nullability(self) -> None:
        required = wrap_expression(
            field_reference(source="input", path=("details",), logical_type=normalize_type(DetailsStruct))
        )
        self.assertIsInstance(required, StructValueExpression)
        self.assertIsInstance(required.pick(lambda item: item.label), StrValueExpression)  # type: ignore[attr-defined]
        selected_nullable = required.pick(lambda item: item.maybe_score)  # type: ignore[attr-defined]
        self.assertIsInstance(selected_nullable, NullableValueExpression)

        optional = wrap_expression(
            field_reference(source="input", path=("details",), logical_type=normalize_type(DetailsStruct | None))
        )
        self.assertIsInstance(optional, StructNullableValueExpression)
        selected = optional.pick(lambda item: item.label)  # type: ignore[attr-defined]
        self.assertIsInstance(selected, NullableValueExpression)
        self.assertEqual(selected.logical_type, NullableType(STR))
        self.assertIsInstance(selected.expression, OperationExpression)


if __name__ == "__main__":
    unittest.main()
