from __future__ import annotations

import json
import unittest
import uuid
from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any

from kg_build_system import Field, Struct, field
from kg_build_system.expressions import (
    ArrayExpression, ArraySelection, BoolExpression, FloatExpression,
    IntExpression, NullableExpression, NullableSelection, StrExpression,
    StructExpression, StructSelection, ValueExpression, ValueSelection, literal,
    select_expression, value_expression, wrap_expression,
)
from kg_build_system.expressions.base import field_reference
from kg_build_system.expressions.codec import decode_expression, encode_expression
from kg_build_system.expressions.models import (
    FieldReferenceExpression, LiteralExpression, OperationExpression,
)
from kg_build_system.types import (
    Array, DATE, INT, NullableType, STR, TIMESTAMP, TIME, UnitType, UUID,
    normalize_type,
)


class DetailsStruct(Struct):
    label: Field[str] = field()
    maybe_score: Field[int | None] = field()


# One portable literal per unit that has no dedicated expression family. A frozen value
# is JSON, so each of these carries its unit on the expression node and its value as the
# canonical text of that unit: ISO-8601 for the temporal units, hyphenated for uuid.
UNFAMILIAR_UNIT_LITERALS: tuple[tuple[Any, UnitType, str], ...] = (
    (date(2026, 1, 1), DATE, "2026-01-01"),
    (time(6, 15), TIME, "06:15:00"),
    (datetime(2026, 7, 14, 6, 15), TIMESTAMP, "2026-07-14T06:15:00"),
    (uuid.UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91"), UUID, "2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91"),
)

# Each unit's own decoder, so a test can say the stored text is still the author's value.
CANONICAL_TEXT_PARSERS: dict[str, Callable[[str], Any]] = {
    "date": date.fromisoformat,
    "time": time.fromisoformat,
    "timestamp": datetime.fromisoformat,
    "uuid": uuid.UUID,
}


def unit_outside_the_vocabulary(name: str) -> UnitType:
    """One UnitType carrying a name the canonical vocabulary refuses to construct."""
    unit = UnitType.__new__(UnitType)
    object.__setattr__(unit, "name", name)
    return unit


class TypedExpressionTests(unittest.TestCase):
    def test_factory_selects_specific_bindable_expression_families(self) -> None:
        self.assertIsInstance(value_expression(True), BoolExpression)
        self.assertIsInstance(value_expression(1), IntExpression)
        self.assertIsInstance(value_expression(1.5), FloatExpression)
        self.assertIsInstance(value_expression("name"), StrExpression)
        nullable = value_expression(None, logical_type=NullableType(STR))
        self.assertIsInstance(nullable, NullableExpression)
        self.assertFalse(hasattr(nullable, "default_to"))

    def test_units_without_a_family_bind_the_generic_expression(self) -> None:
        for _, unit, _ in UNFAMILIAR_UNIT_LITERALS:
            with self.subTest(unit=unit.name):
                expression = wrap_expression(field_reference(
                    source="input", path=("recorded_on",), logical_type=unit,
                ))
                self.assertIs(type(expression), ValueExpression)
                self.assertEqual(expression.logical_type, unit)
        nullable = wrap_expression(field_reference(
            source="input", path=("recorded_on",), logical_type=NullableType(TIMESTAMP),
        ))
        assert isinstance(nullable, NullableExpression)
        self.assertEqual(nullable.non_null_logical_type, TIMESTAMP)

    def test_unit_names_outside_the_vocabulary_are_type_errors(self) -> None:
        for name in ("decimal", "Date", ""):
            with self.subTest(unit=name):
                with self.assertRaisesRegex(TypeError, "unsupported"):
                    wrap_expression(field_reference(
                        source="input", path=("amount",), logical_type=unit_outside_the_vocabulary(name),
                    ))
                with self.assertRaisesRegex(TypeError, "unsupported"):
                    literal("1.10", logical_type=unit_outside_the_vocabulary(name))

    def test_unfamiliar_literals_infer_their_unit_and_carry_their_value(self) -> None:
        for value, unit, text in UNFAMILIAR_UNIT_LITERALS:
            with self.subTest(unit=unit.name):
                expression = value_expression(value)
                self.assertIs(type(expression), ValueExpression)
                self.assertEqual(expression.logical_type, unit)
                model = expression.model
                assert isinstance(model, LiteralExpression)
                self.assertEqual(model.value, text)
                self.assertEqual(CANONICAL_TEXT_PARSERS[unit.name](text), value)

    def test_unfamiliar_literals_round_trip_through_the_expression_codec(self) -> None:
        for value, unit, text in UNFAMILIAR_UNIT_LITERALS:
            with self.subTest(unit=unit.name):
                model = value_expression(value).model
                encoded = encode_expression(model)
                self.assertEqual(encoded["value"], text)
                # The digest and blueprint paths serialise this document with a plain
                # json.dumps, so the encoded value has to be JSON without a default hook.
                self.assertEqual(json.loads(json.dumps(encoded, sort_keys=True)), encoded)
                self.assertEqual(encoded["logical_type"], {"kind": "unit", "name": unit.name})
                self.assertEqual(decode_expression(encoded), model)

    def test_mismatched_literals_name_the_expected_unit(self) -> None:
        cases = (
            ("2026-01-01", DATE, "str"),
            (date(2026, 1, 1), TIMESTAMP, "date"),
            (datetime(2026, 1, 1), DATE, "datetime"),
            ("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91", UUID, "str"),
        )
        for value, unit, actual in cases:
            with self.subTest(unit=unit.name), self.assertRaisesRegex(
                TypeError, f"must be {unit.name}, not {actual}",
            ):
                literal(value, logical_type=unit)

    def test_text_canonical_units_freeze_as_text_whatever_wraps_them(self) -> None:
        self.assertEqual(
            literal(
                [date(2026, 1, 1), None],
                logical_type=normalize_type(Array[date | None]),
            ).value,
            ("2026-01-01", None),
        )
        self.assertEqual(literal(time(9, 30), logical_type=NullableType(TIME)).value, "09:30:00")
        self.assertIsNone(literal(None, logical_type=NullableType(DATE)).value)

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
