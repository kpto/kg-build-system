"""Generated row shapes: join, group_by, unnest and union keep exact types."""
from __future__ import annotations

from typing import assert_type

from kg_build_system import Omitted
from kg_build_system.distribution.languages.data.model.public import (
    DerivedRowSource,
    Field,
    FullJoinedShape,
    GroupedShape,
    InnerJoinedShape,
    LeftJoinedShape,
    RightJoinedShape,
    SourceRelation,
)
from kg_build_system.distribution.languages.data.service.public import field
from kg_build_system.distribution.languages.data.service.public.rows import (
    derive_join,
)
from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel.model.public.types import Array, Nullable, Shape
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


class TaggedEvent(Shape):
    event_id: Selection[Nullable[str]]
    region_id: Selection[Nullable[str]]
    tags: Selection[str]


# ---------------------------------------------------------------- join shapes

inner = Event.row_source().join(
    Reading.row_source(),
    on=lambda event, reading: (
        event.event_id.alter_rows().drop_null(),
        reading.event_id.alter_rows().drop_null(),
    ),
    how="inner",
)
assert_type(
    inner, DerivedRowSource[InnerJoinedShape[Event, Reading, str]],
)
assert_type(inner.shape.on, Selection[str])
assert_type(inner.shape.left, Selection[Event])
assert_type(inner.shape.right, Selection[Reading])

left = Event.row_source().join(
    Reading.row_source(),
    on=lambda event, reading: (event.event_id, reading.event_id),
    how="left",
)
assert_type(
    left, DerivedRowSource[LeftJoinedShape[Event, Reading, Nullable[str]]],
)
assert_type(left.shape.on, Selection[Nullable[str]])
assert_type(left.shape.left, Selection[Event])
assert_type(left.shape.right, Selection[Nullable[Reading]])

right = Event.row_source().join(
    Reading.row_source(),
    on=lambda event, reading: (event.event_id, reading.event_id),
    how="right",
)
assert_type(
    right, DerivedRowSource[RightJoinedShape[Event, Reading, Nullable[str]]],
)
assert_type(right.shape.on, Selection[Nullable[str]])
assert_type(right.shape.left, Selection[Nullable[Event]])
assert_type(right.shape.right, Selection[Reading])

full = Event.row_source().join(
    Reading.row_source(),
    on=lambda event, reading: (event.event_id, reading.event_id),
    how="full",
)
assert_type(
    full, DerivedRowSource[FullJoinedShape[Event, Reading, Nullable[str]]],
)
assert_type(full.shape.on, Selection[Nullable[str]])
assert_type(full.shape.left, Selection[Nullable[Event]])
assert_type(full.shape.right, Selection[Nullable[Reading]])

direct_inner = derive_join(
    Event.row_source(),
    Reading.row_source(),
    on=lambda event, reading: (
        event.event_id.alter_rows().drop_null(),
        reading.event_id.alter_rows().drop_null(),
    ),
)
assert_type(
    direct_inner,
    DerivedRowSource[InnerJoinedShape[Event, Reading, str]],
)

direct_left = derive_join(
    Event.row_source(),
    Reading.row_source(),
    on=lambda event, reading: (event.event_id, reading.event_id),
    how="left",
)
assert_type(
    direct_left,
    DerivedRowSource[LeftJoinedShape[Event, Reading, Nullable[str]]],
)

direct_right = derive_join(
    Event.row_source(),
    Reading.row_source(),
    on=lambda event, reading: (event.event_id, reading.event_id),
    how="right",
)
assert_type(
    direct_right,
    DerivedRowSource[RightJoinedShape[Event, Reading, Nullable[str]]],
)

direct_full = derive_join(
    Event.row_source(),
    Reading.row_source(),
    on=lambda event, reading: (event.event_id, reading.event_id),
    how="full",
)
assert_type(
    direct_full,
    DerivedRowSource[FullJoinedShape[Event, Reading, Nullable[str]]],
)

# --------------------------------------------------------------- group shapes

grouped = Event.row_source().group_by(
    keys=EventKey,
    by=lambda event: {"region_id": event.region_id},
)
assert_type(grouped, DerivedRowSource[GroupedShape[Event, EventKey]])
assert_type(grouped.shape.by, Selection[EventKey])
assert_type(grouped.shape.members, Selection[Array[Event]])

# -------------------------------------------------------------- unnest shape

unnested = Event.row_source().unnest(
    lambda event: event.tags, out=TaggedEvent,
)
assert_type(unnested, DerivedRowSource[TaggedEvent])
assert_type(unnested.shape, type[TaggedEvent])
assert_type(unnested.shape.event_id, Selection[Nullable[str]])
assert_type(unnested.shape.region_id, Selection[Nullable[str]])
assert_type(unnested.shape.tags, Selection[str])

# --------------------------------------------------------------- union shape

combined = Event.row_source().union(Event.row_source())
assert_type(combined, DerivedRowSource[Event])

Event.row_source().union(Reading.row_source())  # pyright: ignore[reportArgumentType]
Event.row_source().group_by(  # pyright: ignore[reportCallIssue]
    by=lambda event: {"region_id": event.region_id},
)
Event.row_source().unnest(lambda event: event.tags)  # pyright: ignore[reportCallIssue]
