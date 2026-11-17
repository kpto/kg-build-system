"""Author-facing row-shape member values and the generated relational shapes.

A ``ShapeField`` names one member of a row: its Python attribute, its external
name and its logical type. The remaining classes are static declarations of the
shape a relational operation generates: a join exposes ``on``, ``left`` and
``right``; a group exposes ``by`` and ``members``. The runtime shape is derived
from the plan and must match the declared members.

Example:
    ```python
    from kg_build_system import Nullable, Selection, Shape

    class EventTag(Shape):
        event_id: Selection[Nullable[str]]
        tag: Selection[str]
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel.model.public.types import (
    Array, LogicalType, Nullable, Shape,
)


@dataclass(frozen=True, slots=True)
class ShapeField:
    """One member of a row shape, in both attribute and external form."""

    attribute: str
    name: str
    logical_type: LogicalType


# ``ClassVar`` keeps member access precise through ``type[Shape]``; pyright
# rejects a type variable inside ``ClassVar``, so each member carries the ignore.
class InnerJoinedShape[L: Shape, R: Shape, K](Shape):
    """The generated shape of an inner join: one matched key per row."""

    on: ClassVar[Selection[K]]  # pyright: ignore[reportGeneralTypeIssues]
    left: ClassVar[Selection[L]]  # pyright: ignore[reportGeneralTypeIssues]
    right: ClassVar[Selection[R]]  # pyright: ignore[reportGeneralTypeIssues]


class LeftJoinedShape[L: Shape, R: Shape, K](Shape):
    """The generated shape of a left join: the right row may be absent."""

    on: ClassVar[Selection[Nullable[K]]]  # pyright: ignore[reportGeneralTypeIssues]
    left: ClassVar[Selection[L]]  # pyright: ignore[reportGeneralTypeIssues]
    right: ClassVar[Selection[Nullable[R]]]  # pyright: ignore[reportGeneralTypeIssues]


class RightJoinedShape[L: Shape, R: Shape, K](Shape):
    """The generated shape of a right join: the left row may be absent."""

    on: ClassVar[Selection[Nullable[K]]]  # pyright: ignore[reportGeneralTypeIssues]
    left: ClassVar[Selection[Nullable[L]]]  # pyright: ignore[reportGeneralTypeIssues]
    right: ClassVar[Selection[R]]  # pyright: ignore[reportGeneralTypeIssues]


class FullJoinedShape[L: Shape, R: Shape, K](Shape):
    """The generated shape of a full join: either row may be absent."""

    on: ClassVar[Selection[Nullable[K]]]  # pyright: ignore[reportGeneralTypeIssues]
    left: ClassVar[Selection[Nullable[L]]]  # pyright: ignore[reportGeneralTypeIssues]
    right: ClassVar[Selection[Nullable[R]]]  # pyright: ignore[reportGeneralTypeIssues]


class GroupedShape[S: Shape, K: Shape](Shape):
    """The generated shape of a group: the key record and its member array."""

    by: ClassVar[Selection[K]]  # pyright: ignore[reportGeneralTypeIssues]
    members: ClassVar[Selection[Array[S]]]  # pyright: ignore[reportGeneralTypeIssues]


__all__ = [
    "FullJoinedShape", "GroupedShape", "InnerJoinedShape", "LeftJoinedShape",
    "RightJoinedShape", "ShapeField",
]
