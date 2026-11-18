"""The iteration chain: append-only events with several references.

An event records one fact about the notebook: a finding was added, a design
changed state, an evaluation was added, or a revision was recorded. Events form
a chain through ``prev``; the object files under ``kgkit/records/`` are
projections of the facts the events carry.

The event shape is::

    {
      "id": "evt-0001",
      "prev": [],
      "kind": "finding_added",
      "at": "2026-11-18T10:00:00+00:00",
      "refs": [{"kind": "finding", "id": "F-0001"}],
      "payload": {"finding": {...}}
    }

``refs`` may name several entities. A revision event names the revision, the
designs it closes and the evaluations it was accepted on.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .config import Project

EVENT_KINDS = (
    "finding_added",
    "design_proposed",
    "design_adopted",
    "design_superseded",
    "design_abandoned",
    "evaluation_added",
    "revision_added",
)
ENTITY_KINDS = ("finding", "change_design", "evaluation", "revision")


def events_dir(project: Project) -> Path:
    return project.path(str(project.config.get("events") or "kgkit/records/events"))


def read_events(project: Project) -> list[dict[str, Any]]:
    """Read the chain in identifier order; the identifier orders the writes."""

    directory = events_dir(project)
    if not directory.is_dir():
        return []
    events: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("id"):
            events.append(value)
    return events


def heads(project: Project) -> list[str]:
    """Return the event identifiers no later event names as ``prev``."""

    events = read_events(project)
    parents = {str(parent) for event in events for parent in event.get("prev") or []}
    return [str(event["id"]) for event in events if str(event["id"]) not in parents]


def next_id(project: Project) -> str:
    used: list[int] = []
    for event in read_events(project):
        suffix = str(event.get("id") or "").removeprefix("evt-")
        if suffix.isdigit():
            used.append(int(suffix))
    return f"evt-{max(used, default=0) + 1:04d}"


def _refs(values: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for value in values:
        kind = str(value.get("kind") or "").strip()
        identifier = str(value.get("id") or "").strip()
        if kind not in ENTITY_KINDS:
            raise ValueError(f"unknown entity kind {kind!r}")
        if not identifier:
            raise ValueError("an event reference needs an id")
        refs.append({"kind": kind, "id": identifier})
    if not refs:
        raise ValueError("an event needs at least one reference")
    return refs


def append(
    project: Project,
    kind: str,
    refs: Iterable[dict[str, Any]],
    payload: dict[str, Any],
    *,
    at: str | None = None,
) -> dict[str, Any]:
    """Append one event to the chain and return it.

    The caller writes the projected object files. An unresolved merge (more than
    one head) refuses the append instead of inventing a parent.
    """

    if kind not in EVENT_KINDS:
        raise ValueError(f"unknown event kind {kind!r}")
    parents = heads(project)
    if len(parents) > 1:
        raise ValueError(
            "unresolved event heads; record a merge resolution first: "
            + ", ".join(parents)
        )
    event = {
        "id": next_id(project),
        "prev": parents,
        "kind": kind,
        "at": at or datetime.now(UTC).isoformat(timespec="seconds"),
        "refs": _refs(refs),
        "payload": payload,
    }
    directory = events_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{event['id']}.json").write_text(
        json.dumps(event, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return event


__all__ = [
    "ENTITY_KINDS",
    "EVENT_KINDS",
    "append",
    "events_dir",
    "heads",
    "next_id",
    "read_events",
]
