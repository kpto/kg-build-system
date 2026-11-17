"""Generated row shapes: static declarations must match the runtime rows."""
from __future__ import annotations

import unittest

from kg_build_system import Omitted
from kg_build_system.distribution.languages.data.model.public import (
    Field,
    SourceRelation,
)
from kg_build_system.distribution.languages.data.service._private.shapes import (
    shape_fields,
)
from kg_build_system.distribution.languages.data.service.public import field
from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel.model.public.types import (
    STR, Array, ArrayType, Nullable, NullableType, Shape, StructType,
)
from tests.distribution.support import TestEstate


class Event(SourceRelation[TestEstate]):
    event_id: Field[str] = field(name="event_id", meaning=Omitted)
    region_id: Field[str] = field(name="region_id", meaning=Omitted)
    tags: Field[Array[str]] = field(name="tags", meaning=Omitted)


class Reading(SourceRelation[TestEstate]):
    reading_id: Field[str] = field(name="reading_id", meaning=Omitted)
    event_id: Field[str] = field(name="event_id", meaning=Omitted)


class EventKey(Shape):
    region_id: Selection[Nullable[str]]


class WrongKeyType(Shape):
    region_id: Selection[Nullable[int]]


class TaggedEvent(Shape):
    event_id: Selection[Nullable[str]]
    region_id: Selection[Nullable[str]]
    tags: Selection[str]


class WrongTagType(Shape):
    event_id: Selection[Nullable[str]]
    region_id: Selection[Nullable[str]]
    tags: Selection[int]


class MissingTag(Shape):
    event_id: Selection[Nullable[str]]
    region_id: Selection[Nullable[str]]


def _fields(rows: object) -> dict[str, object]:
    shape = getattr(rows, "shape")
    return {field.attribute: field for field in shape_fields(shape)}


class JoinShapeTests(unittest.TestCase):
    def test_inner_join_keeps_a_present_key_and_both_rows(self) -> None:
        joined = Event.row_source().join(
            Reading.row_source(),
            on=lambda event, reading: (
                event.event_id.alter_rows().drop_null(),
                reading.event_id.alter_rows().drop_null(),
            ),
            how="inner",
        )

        fields = _fields(joined)
        self.assertEqual(tuple(fields), ("on", "left", "right"))
        self.assertEqual(fields["on"].logical_type, STR)
        self.assertIsInstance(fields["left"].logical_type, StructType)
        self.assertIsInstance(fields["right"].logical_type, StructType)

    def test_outer_joins_make_the_absent_side_and_key_nullable(self) -> None:
        cases = (
            ("left", False, True),
            ("right", True, False),
            ("full", True, True),
        )
        for how, left_nullable, right_nullable in cases:
            with self.subTest(how=how):
                joined = Event.row_source().join(
                    Reading.row_source(),
                    on=lambda event, reading: (
                        event.event_id, reading.event_id,
                    ),
                    how=how,
                )

                fields = _fields(joined)
                self.assertIsInstance(fields["on"].logical_type, NullableType)
                self.assertEqual(
                    isinstance(fields["left"].logical_type, NullableType),
                    left_nullable,
                )
                self.assertEqual(
                    isinstance(fields["right"].logical_type, NullableType),
                    right_nullable,
                )


class GroupShapeTests(unittest.TestCase):
    def test_group_by_exposes_the_key_record_and_the_member_array(self) -> None:
        grouped = Event.row_source().group_by(
            keys=EventKey,
            by=lambda event: {"region_id": event.region_id},
        )

        fields = _fields(grouped)
        self.assertEqual(tuple(fields), ("by", "members"))
        self.assertIsInstance(fields["by"].logical_type, StructType)
        members = fields["members"].logical_type
        self.assertIsInstance(members, ArrayType)
        self.assertIsInstance(members.item, StructType)

    def test_group_by_refuses_keys_that_do_not_match_the_key_shape(self) -> None:
        with self.assertRaisesRegex(TypeError, "key shape"):
            Event.row_source().group_by(
                keys=WrongKeyType,
                by=lambda event: {"region_id": event.region_id},
            )
        with self.assertRaisesRegex(TypeError, "exactly the members"):
            Event.row_source().group_by(
                keys=EventKey,
                by=lambda event: {"other": event.region_id},
            )


class UnnestShapeTests(unittest.TestCase):
    def test_unnest_runtime_shape_matches_the_declared_out_shape(self) -> None:
        unnested = Event.row_source().unnest(
            lambda event: event.tags, out=TaggedEvent,
        )

        self.assertEqual(
            shape_fields(unnested.shape), shape_fields(TaggedEvent),
        )
        fields = _fields(unnested)
        self.assertEqual(fields["event_id"].logical_type, NullableType(STR))
        self.assertEqual(fields["region_id"].logical_type, NullableType(STR))
        self.assertEqual(fields["tags"].logical_type, STR)

    def test_unnest_refuses_an_out_shape_with_a_wrong_type(self) -> None:
        with self.assertRaisesRegex(TypeError, "does not match"):
            Event.row_source().unnest(
                lambda event: event.tags, out=WrongTagType,
            )

    def test_unnest_refuses_an_out_shape_with_a_missing_member(self) -> None:
        with self.assertRaisesRegex(TypeError, "does not match"):
            Event.row_source().unnest(
                lambda event: event.tags, out=MissingTag,
            )


class UnionShapeTests(unittest.TestCase):
    def test_union_accepts_the_same_shape(self) -> None:
        combined = Event.row_source().union(Event.row_source())

        self.assertEqual(shape_fields(combined.shape), shape_fields(Event))

    def test_union_refuses_a_different_shape(self) -> None:
        with self.assertRaisesRegex(TypeError, "same shape"):
            Event.row_source().union(Reading.row_source())


if __name__ == "__main__":
    unittest.main()
