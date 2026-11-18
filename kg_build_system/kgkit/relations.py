"""The relational catalog and the derived iteration timeline.

The catalog has four kinds::

    revision -> evaluation -> finding -> change design -> revision

A revision links the designs it closes, each with the role it had at that
revision; a design links the findings that motivated it and the designs it
supersedes. The reverse links (``superseded_by``, ``revision_links``) are
derived here, never stored twice.

The timeline is the append-only event chain. When a notebook has no event log,
the object files are projected into the same event shape so an older notebook
still reads.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import designs as design_records
from .config import Project, load_project

KIND_ORDER = ("revision", "evaluation", "finding", "change_design")
KIND_LABELS = {
    "revision": "Revision",
    "evaluation": "Evaluation",
    "finding": "Finding",
    "change_design": "Design",
}


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stamp(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")
    except OSError:
        return datetime.now(UTC).isoformat(timespec="seconds")


def _timestamp(value: Any, path: Path) -> str:
    text = str(value or "").strip()
    return text or _stamp(path)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return cleaned or "UNKNOWN"


def _display(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _field(label: str, value: Any, kind: str = "text", tone: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {"label": label, "value": _display(value) if value is not None else "", "kind": kind}
    if tone:
        row["tone"] = tone
    return row


def _metrics(pairs: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in pairs:
        if value is None or value == "":
            continue
        rows.append(
            {
                "name": name,
                "value": float(value) if isinstance(value, (int, float)) else None,
                "value_text": None if isinstance(value, (int, float)) else str(value),
            }
        )
    return rows


def _read_objects(path: Path) -> list[dict[str, Any]]:
    """Read a directory of one-object JSON files, or a legacy JSONL/JSON file."""
    if path.is_dir():
        values: list[dict[str, Any]] = []
        for item in sorted(path.glob("*.json")):
            data = _json(item)
            if data:
                values.append(data)
        return values
    if path.suffix == ".jsonl" and path.is_file():
        values = []
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                values.append(data)
        return values
    if path.is_file():
        data = _json(path)
        return [data] if data else []
    return []


def _records(project: Project, key: str, default: str) -> list[dict[str, Any]]:
    return [
        data
        for data in _read_objects(project.path(str(project.config.get(key) or default)))
        if data.get("id")
    ]


def _role_links(value: Any, key: str, default_role: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for item in _list(value):
        if isinstance(item, str):
            links.append((item, default_role))
        elif isinstance(item, dict) and item.get(key):
            links.append((str(item[key]), str(item.get("role") or default_role)))
    return links


def _revisions_path(project: Project) -> str:
    return str(project.config.get("revisions") or "kgkit/records/revisions")


def _revision_rows(project: Project) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    configured = project.path(_revisions_path(project))
    paths = sorted(configured.glob("*.json")) if configured.is_dir() else (
        [configured] if configured.is_file() else []
    )
    for path in paths:
        data = _json(path)
        counts = _dict(data.get("counts"))
        message = str(data.get("message") or "").strip()
        if not message:
            legacy_title = str(data.get("title") or f"Graph revision {path.stem}")
            legacy_summary = str(data.get("summary") or "")
            message = legacy_title + (f"\n\n{legacy_summary}" if legacy_summary else "")
        lines = message.splitlines()
        subject_index = next((index for index, line in enumerate(lines) if line.strip()), 0)
        subject = lines[subject_index].strip() if lines else f"Graph revision {path.stem}"
        body = "\n".join(lines[subject_index + 1:]).strip()
        design_links = _role_links(data.get("designs"), "design_id", "adopted")
        produced_by = str(data.get("produced_by") or data.get("produced_by_change_design_id") or "")
        if not design_links and produced_by:
            design_links = [(produced_by, "adopted")]
        snapshot = _dict(data.get("snapshot"))
        snapshot_file = str(snapshot.get("file") or "")
        metrics: list[tuple[str, Any]] = []
        for name, key in (
            ("nodes", "nodes"),
            ("edges", "edges"),
            ("evidence_rows", "evidence_rows"),
        ):
            if counts.get(key) is not None:
                metrics.append((name, counts.get(key)))
        evaluation = _dict(data.get("evaluation"))
        metrics.extend(
            [
                ("suites_passed", evaluation.get("passed")),
                ("suites_total", evaluation.get("suites")),
            ]
        )
        rows.append(
            {
                "id": f"KG-{path.stem}",
                "title": subject,
                "summary": body,
                "message": message,
                "created": _timestamp(data.get("recorded_at"), path),
                "source": project.relative(path),
                "fingerprint": str(
                    data.get("blueprint_fingerprint") or data.get("revision") or path.stem
                ),
                "version": str(
                    data.get("version")
                    or data.get("tool_version")
                    or data.get("producer_version")
                    or ""
                ),
                "manifest": str(data.get("manifest") or ""),
                "event_id": str(data.get("event") or ""),
                "metrics": _metrics(metrics),
                "designs": design_links,
                "produced_by": produced_by,
                "evaluations": [str(item) for item in _list(data.get("evaluations"))],
                "view_file": snapshot_file if (project.snapshots_dir / snapshot_file).is_file() else "",
                "view_saved_at": str(snapshot.get("created_at") or ""),
            }
        )
    return rows


def _evaluation_rows(project: Project) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for data in _records(project, "evaluations", "kgkit/records/evaluations"):
        status = str(data.get("status") or "unknown")
        metrics = [
            (str(item.get("name") or ""), item.get("value"))
            for item in _list(data.get("metrics"))
            if isinstance(item, dict)
        ]
        rows.append(
            {
                "id": str(data["id"]),
                "title": f"{str(data.get('mode') or 'evaluation').replace('_', ' ').title()} evaluation",
                "summary": f"{status}" + (f" · {data.get('mode')}" if data.get("mode") else ""),
                "created": str(data.get("created") or ""),
                "source": str(data.get("report") or ""),
                "mode": str(data.get("mode") or ""),
                "status": status,
                "report": str(data.get("report") or ""),
                "revision_id": str(data.get("revision_id") or ""),
                "metrics": _metrics(metrics),
            }
        )
    return rows


def _finding_rows(project: Project) -> list[dict[str, Any]]:
    path = project.path(str(project.config.get("findings") or "kgkit/records/findings"))
    rows: list[dict[str, Any]] = []
    for data in _read_objects(path):
        if not data.get("id"):
            continue
        rows.append(
            {
                "id": str(data["id"]),
                "title": f"{data['id']} · {data.get('layer', 'unspecified')}",
                "summary": str(data.get("observation") or ""),
                "created": _timestamp(data.get("opened"), path),
                "source": project.relative(path),
                "layer": str(data.get("layer") or ""),
                "observation": str(data.get("observation") or ""),
                "decision": str(data.get("decision") or ""),
                "metric": str(data.get("metric") or ""),
                "results": _role_links(data.get("results"), "id", "evidence"),
            }
        )
    return rows


def _change_design_rows(
    project: Project, revisions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    designs = design_records.read_designs(project)
    for design in designs:
        identifier = str(design["id"])
        links = [
            (str(item.get("design_id")), str(item.get("role") or "related"))
            for item in _list(design.get("design_links"))
            if isinstance(item, dict) and item.get("design_id")
        ]
        superseded_by = [
            other["id"]
            for other in designs
            if any(
                item.get("design_id") == identifier and item.get("role") == "supersedes"
                for item in _list(other.get("design_links"))
            )
        ]
        revision_links = [
            {"revision_id": revision["id"], "role": role}
            for revision in revisions
            for design_id, role in revision["designs"]
            if design_id == identifier
        ]
        rows.append(
            {
                "id": identifier,
                "title": str(design.get("title") or identifier),
                "summary": str(design.get("summary") or ""),
                "created": _timestamp(design.get("created"), design_records.designs_dir(project)),
                "source": project.relative(
                    design_records.designs_dir(project) / f"{identifier}.json"
                ),
                "state": str(design.get("state") or "proposed"),
                "findings": [
                    (identifier, role)
                    for identifier, role in _role_links(
                        design.get("findings"), "id", "motivated_by"
                    )
                ],
                "design_links": links,
                "superseded_by": superseded_by,
                "revision_links": revision_links,
            }
        )
    return rows


def _load_rows(project: Project) -> dict[str, list[dict[str, Any]]]:
    revisions = _revision_rows(project)
    return {
        "revision": revisions,
        "evaluation": _evaluation_rows(project),
        "finding": _finding_rows(project),
        "change_design": _change_design_rows(project, revisions),
    }


def _link(rows: list[dict[str, Any]], identifier: str, role: str, kind: str) -> dict[str, Any] | None:
    for row in rows:
        if row["id"] == identifier:
            return {"id": identifier, "kind": kind, "title": row["title"], "role": role}
    return None


def _links_for(kind: str, row: dict[str, Any], rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []

    def add(target_id: str | None, target_kind: str, role: str) -> None:
        if not target_id:
            return
        link = _link(rows.get(target_kind, []), target_id, role, target_kind)
        if link:
            links.append(link)

    if kind == "revision":
        for design_id, role in row.get("designs", []):
            add(design_id, "change_design", role)
        for evaluation_id in row.get("evaluations", []):
            add(evaluation_id, "evaluation", "evaluated_by")
    elif kind == "evaluation":
        add(row.get("revision_id"), "revision", "on_revision")
    elif kind == "finding":
        for design in rows["change_design"]:
            for finding_id, role in design.get("findings", []):
                if finding_id == row["id"]:
                    add(design["id"], "change_design", role)
    elif kind == "change_design":
        for finding_id, role in row.get("findings", []):
            add(finding_id, "finding", role)
        for design_id, role in row.get("design_links", []):
            add(design_id, "change_design", role)
        for link in row.get("revision_links", []):
            add(link["revision_id"], "revision", link["role"])
    return links


def _fields_for(kind: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    if kind == "revision":
        fields = [
            _field("Version", row.get("version") or "not reported"),
            _field("Manifest", (row.get("manifest") or "")[:12] or "not reported", "code"),
            _field("Fingerprint", row.get("fingerprint") or "", "code"),
            _field("Designs", ", ".join(f"{item[0]} ({item[1]})" for item in row.get("designs", []))),
            _field("Snapshot", row.get("view_file") or "not captured", "code"),
        ]
        fields.extend(
            _field(
                metric["name"].replace("_", " ").title(),
                _display(metric["value"]) if metric["value"] is not None else metric["value_text"],
                "metric",
            )
            for metric in row.get("metrics", [])
        )
        return fields
    if kind == "evaluation":
        status = str(row.get("status") or "")
        tone = "accepted" if status == "passed" else "rejected" if status == "failed" else "pending"
        return [
            _field("Status", status, "pill", tone),
            _field("Mode", row.get("mode") or ""),
            _field("Report", row.get("report") or "not reported", "code"),
            *[
                _field(
                    metric["name"].replace("_", " ").title(),
                    _display(metric["value"]) if metric["value"] is not None else metric["value_text"],
                    "metric",
                )
                for metric in row.get("metrics", [])
            ],
        ]
    if kind == "finding":
        return [
            _field("Layer", row.get("layer") or "unspecified"),
            _field("Decision", row.get("decision") or ""),
            _field("Metric", row.get("metric") or "", "metric"),
        ]
    if kind == "change_design":
        state = str(row.get("state") or "proposed")
        tone = {
            "adopted": "accepted",
            "superseded": "pending",
            "abandoned": "rejected",
        }.get(state, "pending")
        return [
            _field("State", state, "pill", tone),
            _field("Supersedes", ", ".join(item[0] for item in row.get("design_links", []) if item[1] == "supersedes")),
            _field("Superseded by", ", ".join(row.get("superseded_by", []))),
            _field("Revisions", ", ".join(link["revision_id"] for link in row.get("revision_links", []))),
        ]
    return []


def _event_title(kind: str, payload: dict[str, Any], fallback: str) -> str:
    if kind in {"design_proposed", "design_adopted", "design_superseded", "design_abandoned"}:
        design = _dict(payload.get("design"))
        return str(design.get("title") or design.get("id") or fallback)
    if kind == "finding_added":
        finding = _dict(payload.get("finding"))
        return str(finding.get("observation") or finding.get("id") or fallback)
    if kind == "evaluation_added":
        evaluation = _dict(payload.get("evaluation"))
        mode = str(evaluation.get("mode") or "evaluation").replace("_", " ").title()
        return f"{mode} evaluation · {evaluation.get('status') or 'unknown'}"
    if kind == "revision_added":
        revision = _dict(payload.get("revision"))
        message = str(revision.get("message") or "").strip()
        first = next((line.strip() for line in message.splitlines() if line.strip()), "")
        return first or str(revision.get("revision") or fallback)
    return fallback


def _synth_events(rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Project object files into the event shape for a notebook with no log."""
    events: list[dict[str, Any]] = []
    for row in rows["finding"]:
        events.append(
            {
                "id": str(row["id"]),
                "kind": "finding_added",
                "at": row["created"],
                "refs": [{"kind": "finding", "id": row["id"]}],
                "payload": {"finding": row},
            }
        )
    for row in rows["change_design"]:
        events.append(
            {
                "id": str(row["id"]),
                "kind": "design_proposed",
                "at": row["created"],
                "refs": [{"kind": "change_design", "id": row["id"]}],
                "payload": {"design": row},
            }
        )
    for row in rows["evaluation"]:
        events.append(
            {
                "id": str(row["id"]),
                "kind": "evaluation_added",
                "at": row["created"],
                "refs": [{"kind": "evaluation", "id": row["id"]}],
                "payload": {"evaluation": row},
            }
        )
    for row in rows["revision"]:
        refs = [{"kind": "revision", "id": row["id"]}]
        refs.extend({"kind": "change_design", "id": item[0]} for item in row["designs"])
        refs.extend({"kind": "evaluation", "id": item} for item in row["evaluations"])
        events.append(
            {
                "id": row["id"],
                "kind": "revision_added",
                "at": row["created"],
                "refs": refs,
                "payload": {"revision": row},
            }
        )
    return events


def _chain(project: Project) -> list[dict[str, Any]]:
    from .events import read_events

    events = read_events(project)
    return events or _synth_events(_load_rows(project))


def timeline(project: Project | None = None) -> list[dict[str, Any]]:
    project = project or load_project()
    revisions = {row["id"]: row for row in _revision_rows(project)}
    rows: list[dict[str, Any]] = []
    for event in _chain(project):
        kind = str(event.get("kind") or "event")
        refs = [
            {"kind": str(ref.get("kind") or ""), "id": str(ref.get("id") or "")}
            for ref in _list(event.get("refs"))
            if isinstance(ref, dict) and ref.get("id")
        ]
        if not refs and event.get("entity_id"):
            refs = [{"kind": str(event.get("entity_kind") or ""), "id": str(event["entity_id"])}]
        revision_id = next((ref["id"] for ref in refs if ref["kind"] == "revision"), "")
        revision = revisions.get(revision_id) or {}
        evaluation = _dict(_dict(event.get("payload")).get("evaluation"))
        if not revision_id and evaluation.get("revision_id"):
            revision_id = str(evaluation["revision_id"])
            revision = revisions.get(revision_id) or {}
        payload = _dict(event.get("payload"))
        timestamp = str(event.get("at") or event.get("timestamp") or "")
        rows.append(
            {
                "id": str(event.get("id") or ""),
                "type": kind,
                "timestamp": timestamp,
                "title": _event_title(kind, payload, str(event.get("title") or event.get("id") or "")),
                **({"message": revision["message"]} if revision.get("message") else {}),
                "refs": refs,
                "entity_id": refs[0]["id"] if refs else "",
                "entity_kind": refs[0]["kind"] if refs else "",
                "revision_id": revision_id or None,
                "view_file": revision.get("view_file") or None,
                "prev": list(event.get("prev") or []),
            }
        )
    return sorted(rows, key=lambda row: (str(row["timestamp"]), str(row["id"])))


def catalog(project: Project | None = None) -> list[dict[str, Any]]:
    project = project or load_project()
    rows = _load_rows(project)
    rank = {kind: index for index, kind in enumerate(KIND_ORDER)}
    objects: list[dict[str, Any]] = []
    for kind in KIND_ORDER:
        for row in rows[kind]:
            objects.append(
                {
                    "id": row["id"],
                    "kind": kind,
                    "title": row["title"],
                    "summary": row.get("summary", ""),
                    "created": row["created"],
                    "source": row.get("source", ""),
                    "fields": _fields_for(kind, row),
                    "links": _links_for(kind, row, rows),
                    **({"view_file": row["view_file"]} if kind == "revision" and row.get("view_file") else {}),
                    **({"message": row["message"]} if kind == "revision" and row.get("message") else {}),
                    **({"event_id": row["event_id"]} if kind == "revision" and row.get("event_id") else {}),
                    **({"state": row["state"]} if kind == "change_design" else {}),
                }
            )
    return sorted(objects, key=lambda item: (rank.get(item["kind"], 9), item["id"]))


def views(project: Project | None = None) -> list[dict[str, Any]]:
    """The viewer timeline: the latest compilation and past revision snapshots."""

    project = project or load_project()
    current = project.snapshots_dir / "current.snapshot.json"
    rows: list[dict[str, Any]] = [
        {
            "kind": "current",
            "label": "Current compilation",
            "file": current.name if current.is_file() else "",
            "created": _stamp(current) if current.is_file() else "",
        }
    ]
    revisions = [row for row in _revision_rows(project) if row.get("view_file")]
    for row in sorted(revisions, key=lambda item: item["created"], reverse=True):
        rows.append(
            {
                "kind": "revision",
                "label": row["id"],
                "revision": row["id"],
                "file": row["view_file"],
                "created": row.get("view_saved_at") or row["created"],
            }
        )
    return rows


def view_file_for(project: Project, revision: str) -> Path | None:
    identifier = revision.removeprefix("KG-")
    path = project.path(_revisions_path(project)) / f"{identifier}.json"
    record = _json(path)
    file = str(_dict(record.get("snapshot")).get("file") or "")
    if not file:
        return None
    candidate = (project.snapshots_dir / file).resolve()
    root = project.snapshots_dir.resolve()
    if root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def known_ids(project: Project | None = None) -> set[str]:
    return {str(row["id"]) for row in catalog(project)}


def graph(project: Project | None = None) -> dict[str, Any]:
    project = project or load_project()
    return {
        "project": project.name,
        "objects": catalog(project),
        "timeline": timeline(project),
        "views": views(project),
    }


__all__ = [
    "KIND_LABELS",
    "KIND_ORDER",
    "catalog",
    "graph",
    "known_ids",
    "timeline",
    "view_file_for",
    "views",
]
