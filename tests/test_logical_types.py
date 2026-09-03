from __future__ import annotations

import datetime
import unittest
import uuid
from typing import Any, get_args, get_type_hints

from kg_build_system.types import (
    Array, ArrayType, BOOL, CANONICAL_UNIT_NAMES, CustomDataType, CustomType, DATE, Date,
    FLOAT, INT, Nullable, NullableType, STR, Struct, StructType, TIME, TIMESTAMP, Time,
    Timestamp, UUID, UnitType, Uuid, array_item, decode_type, encode_type, is_nullable,
    normalize_type, require_non_nullable, require_scalar,
)
from kg_build_system.types.ir import UnitTypeIR
from kg_build_system.types.ir_codec import decode_type_ir, encode_type_ir
from kg_build_system.types.mapping import type_to_ir


_UNITS: tuple[UnitType, ...] = (BOOL, INT, FLOAT, STR, DATE, TIME, TIMESTAMP, UUID)


class ExampleStruct(Struct):
    pass


class ExampleIdentifier(CustomDataType):
    pass


class LogicalTypeTests(unittest.TestCase):
    def test_normalizes_complete_type_vocabulary(self) -> None:
        self.assertEqual(normalize_type(str), STR)
        self.assertEqual(normalize_type(ExampleStruct), StructType(__name__, "ExampleStruct"))
        self.assertEqual(normalize_type(ExampleIdentifier), CustomType(__name__, "ExampleIdentifier"))
        self.assertEqual(normalize_type(Array[int | None]), ArrayType(NullableType(INT)))
        self.assertEqual(normalize_type(Array[str | None] | None), NullableType(ArrayType(NullableType(STR))))
        self.assertEqual(normalize_type(Nullable[str]), NullableType(STR))
        self.assertEqual(normalize_type(Nullable[str | None]), NullableType(STR))

    def test_every_canonical_unit_name_normalizes_from_both_spellings(self) -> None:
        """The lowercase canonical names have exactly one representative class each."""
        self.assertEqual({unit.name for unit in _UNITS}, set(CANONICAL_UNIT_NAMES))
        for annotation, expected in (
            (bool, BOOL), (int, INT), (float, FLOAT), (str, STR),
            (Date, DATE), (datetime.date, DATE),
            (Time, TIME), (datetime.time, TIME),
            (Timestamp, TIMESTAMP), (datetime.datetime, TIMESTAMP),
            (Uuid, UUID), (uuid.UUID, UUID),
        ):
            with self.subTest(annotation=annotation):
                self.assertEqual(normalize_type(annotation), expected)

    def test_temporal_and_identifier_types_compose(self) -> None:
        self.assertEqual(normalize_type(Uuid | None), NullableType(UUID))
        self.assertEqual(
            normalize_type(Array[Timestamp | None]), ArrayType(NullableType(TIMESTAMP)),
        )
        self.assertEqual(
            normalize_type(Array[Date] | None), NullableType(ArrayType(DATE)),
        )

    def test_rejects_open_or_ambiguous_python_types(self) -> None:
        for annotation in (Any, list[str], dict[str, str], str | int, None):
            with self.subTest(annotation=annotation), self.assertRaises(TypeError):
                normalize_type(annotation)

    def test_outer_and_item_nullability_are_independent(self) -> None:
        logical_type = normalize_type(Array[int | None] | None)
        self.assertTrue(is_nullable(logical_type))
        item = array_item(logical_type)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertTrue(is_nullable(item))

    def test_contextual_validation(self) -> None:
        require_scalar(normalize_type(str | None), context="property")
        with self.assertRaisesRegex(TypeError, "property must be a scalar"):
            require_scalar(normalize_type(ExampleStruct), context="property")
        with self.assertRaisesRegex(TypeError, "key must not be nullable"):
            require_non_nullable(normalize_type(str | None), context="key")

    def test_codec_round_trips_nested_types(self) -> None:
        logical_type = normalize_type(Array[ExampleStruct | None] | None)
        self.assertEqual(decode_type(encode_type(logical_type)), logical_type)

    def test_every_canonical_unit_name_round_trips_through_both_codecs(self) -> None:
        for unit in _UNITS:
            with self.subTest(name=unit.name):
                self.assertEqual(decode_type(encode_type(unit)), unit)
                encoded_ir = encode_type_ir(type_to_ir(unit))
                self.assertEqual(encoded_ir, {"kind": "unit", "name": unit.name})
                self.assertEqual(decode_type_ir(encoded_ir), UnitTypeIR(unit.name))

    def test_codecs_reject_a_noncanonical_unit_name(self) -> None:
        payload = {"kind": "unit", "name": "decimal"}
        with self.assertRaisesRegex(ValueError, "unknown unit logical type 'decimal'"):
            decode_type(payload)
        with self.assertRaisesRegex(ValueError, "unknown unit type 'decimal'"):
            decode_type_ir(payload)

    def test_codec_rejects_nested_nullable_ir(self) -> None:
        with self.assertRaises(ValueError):
            decode_type({"kind": "nullable", "value": {"kind": "nullable", "value": {"kind": "unit", "name": "str"}}})

    def test_the_ir_unit_name_literal_is_the_canonical_vocabulary(self) -> None:
        """The IR layer names no models module, so its literal is pinned to the set."""
        self.assertEqual(
            set(get_args(get_type_hints(UnitTypeIR)["name"])),
            set(CANONICAL_UNIT_NAMES),
        )

    def test_models_reject_noncanonical_direct_construction(self) -> None:
        for name in ("decimal", "instant", "interval", "binary", "DATE", ""):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unknown unit logical type"):
                UnitType(name)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            StructType("", "Example")
        with self.assertRaises(ValueError):
            NullableType(NullableType(STR))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
