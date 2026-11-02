"""Mutable state shared by one inference pass.

It lives outside the provider so the shape, override and provenance helpers can
record what they see without passing a long argument list.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import ColumnOverride


@dataclass
class Inference:
    """State shared by one generation pass.

    ``used_names`` is scoped per relation rather than per pass: two tables in one
    group may legitimately have a column of the same name, while two columns of
    one relation may not collide. The override state is scoped per pass instead,
    because a request declares its overrides once for the whole of what it
    generates; the statistics pre-flight stays per relation, because a declared
    path means a different claim in each relation that carries it.
    """

    used_names: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, ColumnOverride] = field(default_factory=dict)
    consumed: set[str] = field(default_factory=set)
    columns: dict[str, set[str]] = field(default_factory=dict)
    nested_members: set[str] = field(default_factory=set)
    #: Normalized schema facts, appended per relation in processing order, from
    #: which the provider computes its source digest.
    schema_facts: list[str] = field(default_factory=list)


__all__ = ["Inference"]
