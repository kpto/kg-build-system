"""The one canonical text form, and the one class-to-unit map behind it."""
from __future__ import annotations

import unittest
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from kg_build_system.expressions import literals
from kg_build_system.expressions.literals import literal
from kg_build_system.modules.targets.file import _canonical_property_value
from kg_build_system.modules.targets.meta_graph.module import _canonical_example_value
from kg_build_system.types import (
    CANONICAL_UNIT_NAMES, TEXT_CANONICAL_UNIT_NAMES, UNIT_BY_REPRESENTATIVE_CLASS,
    Date, Time, Timestamp, Uuid, canonical_value_text,
)

# One sample per text-canonical unit, with the text the vocabulary pins for it: the
# temporal units take ISO-8601, keeping the ``T`` separator ``str()`` replaces with a
# space, and ``uuid`` its lowercase hyphenated spelling.
CANONICAL_TEXT_SAMPLES: tuple[tuple[Date | Time | Timestamp | Uuid, str], ...] = (
    (date(2026, 8, 2), "2026-08-02"),
    (time(14, 20), "14:20:00"),
    (time(10, 0, 0, 123457), "10:00:00.123457"),
    (datetime(2026, 7, 14, 6, 15), "2026-07-14T06:15:00"),
    (datetime(2026, 8, 2, 14, 20, 0, 123456), "2026-08-02T14:20:00.123456"),
    (UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91"), "2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91"),
)


class CanonicalTextFormAgreementTests(unittest.TestCase):
    """Each site that delegates to the shared helper says the very same text.

    The frozen literal, the file target and the meta-graph document are separate
    code paths with separate error wording, and this is what keeps their scalar
    text one fact rather than three that happen to match today.
    """

    def test_the_shared_helper_and_every_site_that_delegates_agree(self) -> None:
        for value, text in CANONICAL_TEXT_SAMPLES:
            with self.subTest(value=repr(value)):
                produced = {
                    "canonical_value_text": canonical_value_text(value),
                    "literal": literal(value).value,
                    "file target": _canonical_property_value(value),
                    "meta-graph document": _canonical_example_value(value),
                }
                for site, form in produced.items():
                    self.assertEqual(form, text, f"{site} is not the canonical text")


class SharedCanonicalVocabularyTests(unittest.TestCase):
    """The consolidations are one fact, so no site can restate it differently."""

    def test_the_literal_class_dispatch_is_the_normalization_map_itself(self) -> None:
        self.assertIs(literals._UNITS_BY_CLASS, UNIT_BY_REPRESENTATIVE_CLASS)
        self.assertEqual(
            {unit.name: value for value, unit in UNIT_BY_REPRESENTATIVE_CLASS.items()},
            literals._CLASSES_BY_UNIT_NAME,
        )

    def test_the_shared_map_covers_the_canonical_vocabulary_exactly_once(self) -> None:
        self.assertEqual(len(UNIT_BY_REPRESENTATIVE_CLASS), len(CANONICAL_UNIT_NAMES))
        self.assertEqual(
            {unit.name for unit in UNIT_BY_REPRESENTATIVE_CLASS.values()},
            set(CANONICAL_UNIT_NAMES),
        )

    def test_the_text_unit_set_is_part_of_the_canonical_vocabulary(self) -> None:
        self.assertEqual(
            TEXT_CANONICAL_UNIT_NAMES, frozenset({"date", "time", "timestamp", "uuid"}),
        )
        self.assertTrue(TEXT_CANONICAL_UNIT_NAMES < set(CANONICAL_UNIT_NAMES))

    def test_a_value_with_no_canonical_text_form_is_refused_by_name(self) -> None:
        for value in (b"bytes", Decimal("1.5"), timedelta(days=1), "2026-08-02"):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(TypeError, type(value).__name__) as caught:
                    canonical_value_text(value)  # type: ignore[arg-type]
                self.assertIn("has no canonical text form", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
