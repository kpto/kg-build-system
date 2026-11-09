"""`Nullable[T]` and `T | None` are one canonical optional type."""
from __future__ import annotations

import unittest

from kg_build_system.kernel import NullableType, STR
from kg_build_system.kernel.model.public.types import Nullable
from kg_build_system.kernel.service.internal.types import normalize_type


class NullableAliasTests(unittest.TestCase):
    def test_the_alias_and_the_union_normalise_identically(self) -> None:
        self.assertEqual(normalize_type(Nullable[str]), NullableType(STR))
        self.assertEqual(normalize_type(str | None), NullableType(STR))

    def test_nested_aliases_flatten(self) -> None:
        self.assertEqual(
            normalize_type(Nullable[Nullable[str]]),
            NullableType(STR),
        )

    def test_an_array_item_keeps_its_nullability(self) -> None:
        from kg_build_system.kernel import Array, ArrayType

        self.assertEqual(
            normalize_type(Array[Nullable[str]]),
            ArrayType(NullableType(STR)),
        )
        self.assertEqual(
            normalize_type(Array[str | None]),
            ArrayType(NullableType(STR)),
        )


if __name__ == "__main__":
    unittest.main()
