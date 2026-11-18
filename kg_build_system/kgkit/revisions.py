"""Record, read and compare revisions.

A revision is the graph closed by a resolved change design set::

    {
      "revision": "<fingerprint>",
      "recorded_at": "...",
      "manifest": "...",
      "counts": {...},
      "designs": [{"design_id": "CD-0001", "role": "adopted"}],
      "produced_by": "CD-0001",
      "evaluations": ["EV-0001"],
      "snapshot": {"file": "...", "created_at": "...", "source": "..."},
      "message": "..."
    }

Recording refuses while any design is unresolved, when no design is adopted,
when a named design's role disagrees with its state, and when no compiled view
can be captured. The design set is supplied by the project's ``revision_facts``
command; the package validates it against the notebook.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import designs, evaluations, events, project_commands, snapshot
from .config import Project

ROLES = ("adopted", "superseded", "abandoned")


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def revisions_dir(project: Project) -> Path:
    return project.path(str(project.config.get("revisions") or "kgkit/records/revisions"))


def _revision_files(project: Project) -> list[Path]:
    directory = revisions_dir(project)
    if directory.is_dir():
        return sorted(directory.glob("*.json"))
    return [directory] if directory.is_file() else []


def list_revisions(project: Project) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in _revision_files(project):
        data = _json(path)
        rows.append(
            {
                "revision": data.get("revision"),
                "path": str(path),
                "recorded_at": data.get("recorded_at"),
                "counts": data.get("counts", {}),
                "designs": data.get("designs", []),
                "evaluations": data.get("evaluations", []),
                "snapshot": data.get("snapshot", {}),
            }
        )
    return {"ok": True, "revisions": rows}


def linked_revisions(project: Project, identifier: str) -> list[str]:
    """Return the revision ids that name a design."""

    found: list[str] = []
    for path in _revision_files(project):
        data = _json(path)
        for item in data.get("designs") or []:
            if isinstance(item, dict) and item.get("design_id") == identifier:
                found.append(f"KG-{path.stem}")
                break
    return found


def _normalise_designs(
    project: Project, facts: dict[str, Any]
) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    raw = facts.get("designs")
    values: list[dict[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                errors.append("revision_facts.designs entries must be objects")
                continue
            identifier = str(item.get("design_id") or item.get("id") or "").strip()
            role = str(item.get("role") or "adopted").strip()
            if not identifier:
                errors.append("revision_facts.designs entry has no design_id")
                continue
            values.append({"design_id": identifier, "role": role})
    elif raw not in (None, ""):
        errors.append("revision_facts.designs must be a list")
    if not values:
        produced_by = str(
            facts.get("produced_by_change_design_id") or facts.get("produced_by") or ""
        ).strip()
        if produced_by:
            values = [{"design_id": produced_by, "role": "adopted"}]
        else:
            errors.append("revision_facts named no designs; return designs: [{design_id, role}]")
    seen: set[str] = set()
    for item in values:
        identifier = item["design_id"]
        role = item["role"]
        if identifier in seen:
            errors.append(f"{identifier} appears twice in the revision's designs")
            continue
        seen.add(identifier)
        if role not in ROLES:
            errors.append(f"{identifier} has role {role}; use adopted, superseded or abandoned")
            continue
        design = designs.read_design(project, identifier)
        if design is None:
            errors.append(f"design {identifier} does not exist")
            continue
        state = str(design.get("state") or "proposed")
        if state != role:
            errors.append(
                f"{identifier} is {state} in the notebook but the revision names it {role}"
            )
    if not any(item["role"] == "adopted" for item in values):
        errors.append("the revision has no adopted design")
    produced_by = str(
        facts.get("produced_by_change_design_id") or facts.get("produced_by") or ""
    ).strip()
    if produced_by and produced_by not in {
        item["design_id"] for item in values if item["role"] == "adopted"
    }:
        errors.append(f"produced_by {produced_by} is not one of the adopted designs")
    return values, errors


def _evaluation_ids(project: Project, facts: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    raw = facts.get("evaluations")
    values = [str(item) for item in raw] if isinstance(raw, list) else []
    if values:
        for identifier in values:
            if evaluations.read_evaluation(project, identifier) is None:
                errors.append(f"evaluation {identifier} does not exist")
        return values, errors
    current = evaluations.latest(project)
    return ([str(current["id"])] if current else []), errors


def record_revision(project: Project, message: str | None = None) -> dict[str, Any]:
    unresolved = designs.gate(project)
    if unresolved:
        return {"ok": False, "error": "; ".join(unresolved), "designs": unresolved}
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
    facts = {
        key: value
        for key, value in facts.items()
        if key not in {"command", "exit_code", "stderr", "ok", "title", "summary"}
    }
    design_links, errors = _normalise_designs(project, facts)
    evaluation_ids, evaluation_errors = _evaluation_ids(project, facts)
    errors.extend(evaluation_errors)
    if errors:
        return {"ok": False, "error": "; ".join(errors), "designs": errors}
    try:
        captured = snapshot.capture(project, revision=revision)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}

    report = _evaluation_summary(project, evaluation_ids)
    recorded_at = datetime.now(UTC).isoformat(timespec="seconds")
    text = str(message if message is not None else facts.get("message") or "").strip()
    if not text:
        text = f"Graph revision {revision}"
    facts.update(
        {
            "revision": revision,
            "blueprint_fingerprint": str(facts.get("blueprint_fingerprint") or revision),
            "recorded_at": recorded_at,
            "message": text,
            "designs": design_links,
            "evaluations": evaluation_ids,
            "snapshot": {
                "file": captured["file"],
                "created_at": captured["created_at"],
                "source": captured["source"],
            },
        }
    )
    facts["evaluation"] = report
    directory = revisions_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{revision}.json"
    manifest = str(facts.get("manifest") or "")
    if path.exists():
        existing = _json(path)
        if existing.get("manifest") != manifest and manifest:
            path = directory / f"{revision}-{manifest[:8]}.json"
    refs = [{"kind": "revision", "id": f"KG-{revision}"}]
    refs.extend({"kind": "change_design", "id": item["design_id"]} for item in design_links)
    refs.extend({"kind": "evaluation", "id": identifier} for identifier in evaluation_ids)
    event = events.append(
        project,
        "revision_added",
        refs,
        {"revision": {**facts, "id": f"KG-{revision}"}},
        at=recorded_at,
    )
    facts["event"] = event["id"]
    path.write_text(json.dumps(facts, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(path),
        "event": str(events.events_dir(project) / f"{event['id']}.json"),
        "facts": facts,
    }


def _evaluation_summary(project: Project, identifiers: list[str]) -> dict[str, Any]:
    for identifier in reversed(identifiers):
        evaluation = evaluations.read_evaluation(project, identifier)
        if evaluation is None:
            continue
        metrics = evaluation.get("metrics")
        metrics = metrics if isinstance(metrics, list) else []
        passed = next(
            (item.get("value") for item in metrics if item.get("name") == "suites_passed"),
            None,
        )
        total = next(
            (item.get("value") for item in metrics if item.get("name") == "suites_total"),
            None,
        )
        return {
            "status": evaluation.get("status"),
            "passed": int(passed) if isinstance(passed, (int, float)) else None,
            "suites": int(total) if isinstance(total, (int, float)) else None,
            "evaluation": identifier,
        }
    return {}


def compare_revisions(project: Project, before: str, after: str) -> dict[str, Any]:
    directory = revisions_dir(project)
    before_path = directory / f"{before.removeprefix('KG-')}.json"
    after_path = directory / f"{after.removeprefix('KG-')}.json"
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
        "counts": {"before": first.get("counts"), "after": second.get("counts")},
        "designs": {"before": first.get("designs"), "after": second.get("designs")},
        "evaluation": {"before": first.get("evaluation"), "after": second.get("evaluation")},
    }


__all__ = [
    "compare_revisions",
    "linked_revisions",
    "list_revisions",
    "record_revision",
    "revisions_dir",
]
