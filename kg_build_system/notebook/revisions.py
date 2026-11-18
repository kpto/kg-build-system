"""Read, record and compare revision pins.

A revision is the tuple ``(manifest, blueprint fingerprint, build counts,
evaluation summary)``. The project supplies the facts; the package owns the
file shape, the overwrite rule and the comparison guard.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Project
from . import project_commands


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _report(project: Project) -> dict[str, Any]:
    for value in project.paths(project.config.get("evaluation_reports")):
        report = _json(value)
        if report:
            return report
    return {}


def revisions_dir(project: Project) -> Path:
    value = str(project.config.get("revisions") or "revisions")
    return project.path(value)


def list_revisions(project: Project) -> dict[str, Any]:
    directory = revisions_dir(project)
    rows: list[dict[str, Any]] = []
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            data = _json(path)
            rows.append(
                {
                    "revision": data.get("revision"),
                    "path": str(path),
                    "recorded_at": data.get("recorded_at"),
                    "counts": data.get("counts", {}),
                    "evaluation": data.get("evaluation", {}),
                }
            )
    return {"ok": True, "revisions": rows}


def _view_file(project: Project, revision: str) -> str | None:
    """Return the latest captured viewer file for a revision, if any."""

    directory = project.snapshots_dir
    if not directory.is_dir():
        return None
    latest: tuple[str, str] | None = None
    for meta_path in directory.glob("*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        value = str(meta.get("revision") or "").strip()
        file = str(meta.get("snapshot_file") or "").strip()
        if value != revision or not file or not (directory / file).is_file():
            continue
        saved_at = str(meta.get("saved_at") or "")
        if latest is None or saved_at > latest[0]:
            latest = (saved_at, file)
    return latest[1] if latest else None


def _event_heads(project: Project) -> list[str]:
    directory = project.path(str(project.config.get("events") or "notebook/records/events"))
    if not directory.is_dir():
        return []
    events = [_json(path) for path in sorted(directory.glob("*.json"))]
    children = {parent for event in events for parent in event.get("prev", [])}
    return [str(event["id"]) for event in events if event.get("id") and event["id"] not in children]


def record_revision(project: Project, message: str | None = None) -> dict[str, Any]:
    facts = project_commands.run(project, "revision_facts")
    if not facts.get("ok"):
        return {
            "ok": False,
            "error": facts.get("error") or "revision_facts failed",
            "command": facts.get("command"),
        }
    revision = str(facts.get("revision") or "").strip()
    if not revision:
        return {"ok": False, "error": "revision_facts returned no revision"}
    report = _report(project)
    facts = dict(facts)
    for key in ("command", "exit_code", "stderr", "ok"):
        facts.pop(key, None)
    facts["evaluation"] = report.get("summary", {}) if report else {}
    facts["recorded_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    text = str(message if message is not None else facts.get("message") or "").strip()
    if not text:
        text = f"Graph revision {revision}"
    facts["message"] = text
    facts.pop("title", None)
    facts.pop("summary", None)
    directory = revisions_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{revision}.json"
    manifest = str(facts.get("manifest") or "")
    if path.exists():
        existing = _json(path)
        if existing.get("manifest") != manifest and manifest:
            path = directory / f"{revision}-{manifest[:8]}.json"
    heads = _event_heads(project)
    if len(heads) > 1:
        return {
            "ok": False,
            "error": "unresolved event heads; record a merge resolution first",
            "heads": heads,
        }
    path.write_text(json.dumps(facts, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    events = project.path(str(project.config.get("events") or "notebook/records/events"))
    events.mkdir(parents=True, exist_ok=True)
    event_id = f"evt-{revision}"
    event = {
        "id": event_id,
        "prev": heads,
        "kind": "kg_edited",
        "at": facts["recorded_at"],
        "title": next(
            (line.strip() for line in text.splitlines() if line.strip()),
            f"Graph revision {revision}",
        ),
        "revision": f"KG-{revision}",
        "entity_id": f"KG-{revision}",
        "entity_kind": "revision",
        "view_file": _view_file(project, revision),
    }
    (events / f"{event_id}.json").write_text(
        json.dumps(event, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"ok": True, "path": str(path), "event": str(events / f"{event_id}.json"), "facts": facts}


def compare_revisions(project: Project, before: str, after: str) -> dict[str, Any]:
    directory = revisions_dir(project)
    before_path = directory / f"{before}.json"
    after_path = directory / f"{after}.json"
    if not before_path.is_file() or not after_path.is_file():
        return {
            "ok": False,
            "error": f"revision file not found: {before_path if not before_path.is_file() else after_path}",
        }
    first = _json(before_path)
    second = _json(after_path)
    if first.get("manifest") != second.get("manifest"):
        return {
            "ok": False,
            "error": "revisions use different data manifests; the comparison is not valid",
        }
    return {
        "ok": True,
        "revision": {"before": before, "after": after},
        "counts": {
            "before": first.get("counts"),
            "after": second.get("counts"),
        },
        "evaluation": {
            "before": first.get("evaluation"),
            "after": second.get("evaluation"),
        },
    }


__all__ = [
    "compare_revisions",
    "list_revisions",
    "record_revision",
    "revisions_dir",
]
