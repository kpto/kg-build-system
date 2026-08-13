from __future__ import annotations

import unittest
from typing import Any

from kg_build_system.types import (
    Array, ArrayType, CustomDataType, CustomType, INT, Nullable, NullableType, STR, Struct,
    StructType, UnitType, array_item, decode_type, encode_type, is_nullable, normalize_type,
    require_non_nullable, require_scalar,
)


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

    def test_codec_rejects_nested_nullable_ir(self) -> None:
        with self.assertRaises(ValueError):
            decode_type({"kind": "nullable", "value": {"kind": "nullable", "value": {"kind": "unit", "name": "str"}}})

    def test_models_reject_noncanonical_direct_construction(self) -> None:
        with self.assertRaises(ValueError):
            UnitType("decimal")
        with self.assertRaises(ValueError):
            StructType("", "Example")
        with self.assertRaises(ValueError):
            NullableType(NullableType(STR))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
