"""Change designs: the argument a graph change must carry.

A design is proposed, then resolved as adopted, superseded or abandoned. Only an
adopted design authorizes declarations; a superseded or abandoned design is kept
so a revision can explain the paths the project did not take.

Links between designs are stored once: the superseding design carries
``{"design_id": ..., "role": "supersedes"}``. The reverse ``superseded_by`` is
derived by the catalog, not stored twice.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from . import events
from .config import Project

STATES = ("proposed", "adopted", "superseded", "abandoned")
RESOLVED_STATES = ("adopted", "superseded", "abandoned")
STATE_EVENTS = {
    "adopted": "design_adopted",
    "superseded": "design_superseded",
    "abandoned": "design_abandoned",
}
LINK_ROLES = ("supersedes", "related")


def designs_dir(project: Project) -> Path:
    return project.path(str(project.config.get("change_designs") or "kgkit/records/designs"))


def read_designs(project: Project) -> list[dict[str, Any]]:
    directory = designs_dir(project)
    if not directory.is_dir():
        return []
    designs: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("id"):
            designs.append(value)
    return designs


def read_design(project: Project, identifier: str) -> dict[str, Any] | None:
    for design in read_designs(project):
        if design.get("id") == identifier:
            return design
    return None


def next_id(project: Project) -> str:
    used: list[int] = []
    for design in read_designs(project):
        suffix = str(design.get("id") or "").removeprefix("CD-")
        if suffix.isdigit():
            used.append(int(suffix))
    return f"CD-{max(used, default=0) + 1:04d}"


def _write(project: Project, design: dict[str, Any]) -> Path:
    directory = designs_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{design['id']}.json"
    path.write_text(json.dumps(design, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _finding_links(values: Iterable[Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for value in values:
        if isinstance(value, str):
            links.append({"id": value, "role": "motivated_by"})
        elif isinstance(value, dict) and value.get("id"):
            links.append({"id": str(value["id"]), "role": str(value.get("role") or "motivated_by")})
    return links


def _design_links(
    project: Project,
    supersedes: Iterable[str],
    related: Iterable[str],
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for role, values in (("supersedes", supersedes), ("related", related)):
        for value in values:
            identifier = str(value).strip()
            if not identifier:
                continue
            if read_design(project, identifier) is None:
                raise ValueError(f"design {identifier} does not exist")
            links.append({"design_id": identifier, "role": role})
    return links


def propose(
    project: Project,
    *,
    title: str,
    summary: str = "",
    findings: Iterable[Any] = (),
    supersedes: Iterable[str] = (),
    related: Iterable[str] = (),
) -> dict[str, Any]:
    """Create a proposed design and append its ``design_proposed`` event."""

    text = str(title or "").strip()
    if not text:
        raise ValueError("a design needs a title")
    design = {
        "id": next_id(project),
        "title": text,
        "summary": str(summary or "").strip(),
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "state": "proposed",
        "findings": _finding_links(findings),
        "design_links": _design_links(project, supersedes, related),
    }
    event = events.append(
        project,
        "design_proposed",
        [{"kind": "change_design", "id": design["id"]}],
        {"design": {key: value for key, value in design.items() if key != "last_event"}},
    )
    design["last_event"] = event["id"]
    _write(project, design)
    return design


def linked_revisions(project: Project, identifier: str) -> list[str]:
    """Revisions that name this design; a linked design is immutable."""

    from .revisions import linked_revisions as _linked

    return _linked(project, identifier)


def set_state(
    project: Project,
    identifier: str,
    state: str,
    *,
    by: str | None = None,
) -> dict[str, Any]:
    """Resolve one design and append the matching state event."""

    if state not in RESOLVED_STATES:
        raise ValueError(f"state must be one of {', '.join(RESOLVED_STATES)}")
    design = read_design(project, identifier)
    if design is None:
        raise ValueError(f"design {identifier} does not exist")
    current = str(design.get("state") or "proposed")
    if current in ("superseded", "abandoned"):
        raise ValueError(f"design {identifier} is already {current}; a terminal design is immutable")
    revisions = linked_revisions(project, identifier)
    if revisions:
        raise ValueError(
            f"design {identifier} is linked to {', '.join(revisions)}; "
            "record a new design instead of changing it"
        )
    refs = [{"kind": "change_design", "id": identifier}]
    if state == "superseded":
        replacement = str(by or "").strip()
        if not replacement:
            raise ValueError("a superseded design needs --by <design id>")
        if replacement == identifier:
            raise ValueError("a design cannot supersede itself")
        replacement_design = read_design(project, replacement)
        if replacement_design is None:
            raise ValueError(f"design {replacement} does not exist")
        links = list(replacement_design.get("design_links") or [])
        if not any(
            link.get("design_id") == identifier and link.get("role") == "supersedes"
            for link in links
        ):
            raise ValueError(
                f"design {replacement} does not link {identifier} with role supersedes; "
                f"run: kbs notebook design link --from {replacement} --to {identifier} --role supersedes"
            )
        refs.append({"kind": "change_design", "id": replacement})
    design["state"] = state
    design["resolved_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    event = events.append(
        project,
        STATE_EVENTS[state],
        refs,
        {"design": {key: value for key, value in design.items() if key != "last_event"}},
    )
    design["last_event"] = event["id"]
    _write(project, design)
    return design


def link(project: Project, source: str, target: str, role: str) -> dict[str, Any]:
    """Add one design-to-design link to the source design."""

    if role not in LINK_ROLES:
        raise ValueError(f"role must be one of {', '.join(LINK_ROLES)}")
    design = read_design(project, source)
    if design is None:
        raise ValueError(f"design {source} does not exist")
    if read_design(project, target) is None:
        raise ValueError(f"design {target} does not exist")
    if source == target:
        raise ValueError("a design cannot link itself")
    links = list(design.get("design_links") or [])
    if any(item.get("design_id") == target and item.get("role") == role for item in links):
        return design
    links.append({"design_id": target, "role": role})
    design["design_links"] = links
    _write(project, design)
    return design


def gate(project: Project) -> list[str]:
    """Return the reasons a revision may not be recorded yet.

    Resolution is a notebook fact: every design is terminal, at least one is
    adopted, and a superseded design is superseded by a design that says so.
    """

    designs = read_designs(project)
    if not designs:
        return ["no change design; run: kbs notebook design new --title ..."]
    errors: list[str] = []
    for design in designs:
        state = str(design.get("state") or "proposed")
        identifier = str(design["id"])
        if state not in RESOLVED_STATES:
            errors.append(f"{identifier} is {state}; adopt, supersede or abandon it before revise")
        if state == "superseded":
            incoming = [
                other
                for other in designs
                if any(
                    item.get("design_id") == identifier and item.get("role") == "supersedes"
                    for item in other.get("design_links") or []
                )
            ]
            if not incoming:
                errors.append(f"{identifier} is superseded but no design names it as superseded")
    if not any(str(design.get("state")) == "adopted" for design in designs):
        errors.append("no adopted design; a revision needs at least one adopted design")
    return errors


__all__ = [
    "LINK_ROLES",
    "RESOLVED_STATES",
    "STATES",
    "designs_dir",
    "gate",
    "link",
    "linked_revisions",
    "next_id",
    "propose",
    "read_design",
    "read_designs",
    "set_state",
]
