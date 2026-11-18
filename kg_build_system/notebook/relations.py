"""The relational catalog and the derived iteration timeline.

The package models a knowledge graph project as typed entities:

    revision -> evaluation_run -> result -> finding -> design -> revision

Findings and proposals are supporting entities referenced by a change design.
They are not iteration rows. The timeline is derived from event files, with a
legacy projection from the object files when no event log exists.

The catalog is loaded from the tracked ``notebook/`` directory; there is no
database.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Project, load_project

KIND_ORDER = (
    "revision",
    "evaluation_design",
    "evaluation_run",
    "result",
    "finding",
    "proposal",
    "change_design",
)
KIND_LABELS = {
    "revision": "Revision",
    "evaluation_design": "Evaluation design",
    "evaluation_run": "Evaluation run",
    "result": "Result",
    "finding": "Finding",
    "proposal": "Proposal",
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


def _json_list(path: Path) -> list[Any]:
    if not path.is_file():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("items", "rows", "entries", "designs"):
            if isinstance(value.get(key), list):
                return value[key]
    return []


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


def _unique(used: dict[str, int], identifier: str) -> str:
    count = used.get(identifier, 0) + 1
    used[identifier] = count
    return identifier if count == 1 else f"{identifier}-{count}"


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


def _report_paths(project: Project) -> list[Path]:
    paths: list[Path] = []
    for path in project.paths(project.config.get("evaluation_reports")):
        if path.is_file():
            paths.append(path)
    eval_dir = project.path("eval")
    if eval_dir.is_dir():
        for path in sorted(eval_dir.glob("*.json")):
            if any(path.resolve() == item.resolve() for item in paths):
                continue
            data = _json(path)
            if data.get("format") == "kg-eval-report" or (
                "mode" in data and "suites" in data
            ):
                paths.append(path)
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _audit_metrics(project: Project) -> dict[str, Any]:
    reports = _report_paths(project)
    if not reports:
        return {}
    report = _json(reports[0])
    suites = _dict(report.get("suites"))
    return _dict(_dict(suites.get("audit")).get("metrics"))


def _revision_rows(project: Project) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    configured = project.path(str(project.config.get("revisions") or "revisions"))
    paths = sorted(configured.glob("*.json")) if configured.is_dir() else (
        [configured] if configured.is_file() else []
    )
    audit = _audit_metrics(project)
    for path in paths:
        data = _json(path)
        evaluation = _dict(data.get("evaluation"))
        counts = _dict(data.get("counts"))
        recorded = _dict(data.get("graph"))
        metrics: list[tuple[str, Any]] = []
        for name, key in (
            ("nodes", "nodes"),
            ("edges", "edges"),
            ("evidence_rows", "evidence_rows"),
        ):
            value = recorded.get(key)
            if value is None:
                value = audit.get(
                    {"nodes": "node_count", "edges": "edge_count"}.get(name, "record_count")
                )
            if value is not None:
                metrics.append((name, value))
        if evaluation:
            metrics.extend(
                [
                    ("suites_passed", evaluation.get("passed")),
                    ("suites_total", evaluation.get("suites")),
                ]
            )
        source_rows = sum(
            value for value in counts.values() if isinstance(value, (int, float))
        )
        if source_rows:
            metrics.append(("source_rows", source_rows))
        message = str(data.get("message") or "").strip()
        if not message:
            legacy_title = str(data.get("title") or f"Graph revision {path.stem}")
            legacy_summary = str(data.get("summary") or "")
            message = legacy_title + (f"\n\n{legacy_summary}" if legacy_summary else "")
        lines = message.splitlines()
        subject_index = next((index for index, line in enumerate(lines) if line.strip()), 0)
        subject = lines[subject_index].strip() if lines else f"Graph revision {path.stem}"
        body = "\n".join(lines[subject_index + 1:]).strip()
        rows.append(
            {
                "id": f"KG-{path.stem}",
                "title": subject,
                "summary": body,
                "message": message,
                "created": _timestamp(data.get("recorded_at"), path),
                "source": project.relative(path),
                "fingerprint": str(data.get("revision") or path.stem),
                "version": str(
                    data.get("version")
                    or data.get("tool_version")
                    or data.get("producer_version")
                    or ""
                ),
                "manifest": str(data.get("manifest") or ""),
                "metrics": _metrics(metrics),
                "produced_by": data.get("produced_by_change_design_id")
                or data.get("produced_by"),
            }
        )
    views = _view_files(project)
    for row in rows:
        view = views.get(str(row["id"]))
        row["view_file"] = view["file"] if view else ""
        row["view_saved_at"] = view["saved_at"] if view else ""
    return rows


def _evaluation_design_rows(project: Project) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    design_path = project.path(str(project.config.get("eval_design") or "eval/design.json"))
    design = _json(design_path)
    design_created = _timestamp(design.get("recorded_at"), design_path)
    design_source = project.relative(design_path)
    for value in _list(design.get("modes")):
        mode = _dict(value)
        name = str(mode.get("name") or "").strip()
        if not name:
            continue
        identifier = f"ED-{_slug(name)}"
        if identifier in seen:
            continue
        seen.add(identifier)
        runs = [str(item) for item in _list(mode.get("runs"))]
        skips = [str(item) for item in _list(mode.get("skips"))]
        summary = str(mode.get("note") or "")
        if not summary:
            summary = (
                f"Runs {', '.join(runs)}." if runs else "Evaluation design."
            )
        rows.append(
            {
                "id": identifier,
                "title": f"{name.replace('_', ' ').title()} evaluation design",
                "summary": summary,
                "created": design_created,
                "source": design_source,
                "mode": name,
                "runs": runs,
                "skips": skips,
            }
        )
    for report_path in _report_paths(project):
        report = _json(report_path)
        name = str(report.get("mode") or report_path.stem).strip()
        identifier = f"ED-{_slug(name)}"
        if not name or identifier in seen:
            continue
        seen.add(identifier)
        rows.append(
            {
                "id": identifier,
                "title": f"{name.replace('_', ' ').title()} evaluation design",
                "summary": "Evaluation design discovered from an evaluation report.",
                "created": _stamp(report_path),
                "source": project.relative(report_path),
                "mode": name,
                "runs": [],
                "skips": [],
            }
        )
    return rows


def _suite_status(suites: dict[str, Any]) -> str:
    statuses = [str(_dict(value).get("status") or "") for value in suites.values()]
    if "failed" in statuses:
        return "failed"
    if "passed" in statuses:
        return "passed"
    if statuses and all(status == "skipped" for status in statuses):
        return "skipped"
    return "unknown"


def _revision_id_for(
    revisions: list[dict[str, Any]], fingerprint: str
) -> str | None:
    if not fingerprint:
        return None
    if fingerprint.startswith("KG-"):
        identifier = fingerprint
    else:
        identifier = f"KG-{fingerprint}"
    for row in revisions:
        if row["id"] == identifier or row["fingerprint"] == fingerprint:
            return str(row["id"])
    return None


def _evaluation_rows(
    project: Project,
    revisions: list[dict[str, Any]],
    designs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    design_by_mode = {row["mode"]: row for row in designs}
    used_runs: dict[str, int] = {}
    used_results: dict[str, int] = {}
    for report_path in _report_paths(project):
        report = _json(report_path)
        if not report:
            continue
        mode = str(report.get("mode") or report_path.stem).strip()
        summary = _dict(report.get("summary"))
        suites = _dict(report.get("suites"))
        status = str(summary.get("status") or _suite_status(suites))
        revision_info = _dict(report.get("revision"))
        fingerprint = str(
            revision_info.get("blueprint_fingerprint")
            or revision_info.get("revision")
            or ""
        )
        revision_id = _revision_id_for(revisions, fingerprint)
        design = design_by_mode.get(mode)
        design_id = design["id"] if design else f"ED-{_slug(mode)}"
        created = _stamp(report_path)
        run_id = _unique(used_runs, f"EV-{_slug(mode)}")
        result_id = _unique(used_results, f"ER-{_slug(mode)}")
        passed = summary.get("passed")
        total = summary.get("suites")
        summary_text = (
            f"{passed}/{total} suites passed"
            if passed is not None and total is not None
            else status
        )
        runs.append(
            {
                "id": run_id,
                "title": f"{mode.replace('_', ' ').title()} evaluation",
                "summary": summary_text,
                "created": created,
                "source": project.relative(report_path),
                "revision_id": revision_id,
                "evaluation_design_id": design_id,
                "status": status,
            }
        )
        metric_pairs: list[tuple[str, Any]] = []
        for name, key in (
            ("suites_passed", "passed"),
            ("suites_total", "suites"),
            ("suites_failed", "failed"),
            ("suites_skipped", "skipped"),
        ):
            if summary.get(key) is not None:
                metric_pairs.append((name, summary.get(key)))
        audit = _dict(_dict(suites.get("audit")).get("metrics"))
        for name, key in (
            ("nodes", "node_count"),
            ("edges", "edge_count"),
            ("evidence_rows", "record_count"),
        ):
            if audit.get(key) is not None:
                metric_pairs.append((name, audit.get(key)))
        results.append(
            {
                "id": result_id,
                "title": f"{mode.replace('_', ' ').title()} result",
                "summary": summary_text,
                "created": created,
                "source": project.relative(report_path),
                "evaluation_run_id": run_id,
                "report": project.relative(report_path),
                "metrics": _metrics(metric_pairs),
            }
        )
    return runs, results


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


def _finding_rows(project: Project) -> list[dict[str, Any]]:
    path = project.path(str(project.config.get("findings") or "notebook/records/findings"))
    rows: list[dict[str, Any]] = []
    for data in _read_objects(path):
        if not data.get("id"):
            continue
        if str(data.get("layer") or "") == "proposal":
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
                "metric": str(data.get("metric") or ""),
                "state": str(data.get("state") or "proposed"),
                "note": str(data.get("decision") or ""),
                "results": _evidence_links(data.get("results")),
            }
        )
    return rows


def _evidence_links(value: Any) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for item in _list(value):
        if isinstance(item, str):
            links.append((item, "evidence"))
        elif isinstance(item, dict) and item.get("id"):
            links.append((str(item["id"]), str(item.get("role") or "evidence")))
    return links


def _proposal_rows(project: Project) -> list[dict[str, Any]]:
    path = project.path(str(project.config.get("proposals") or "notebook/records/proposals"))
    rows: list[dict[str, Any]] = []
    for data in _read_objects(path):
        if not data.get("id"):
            continue
        if path.is_dir() and str(data.get("layer") or "") not in {"", "proposal"}:
            continue
        source = str(data["id"])
        suffix = source.rsplit("-", 1)[-1] if "-" in source else _slug(source)
        identifier = source if source.upper().startswith("P-") else f"P-{suffix}"
        rows.append(
            {
                "id": identifier,
                "title": f"{source} · proposal",
                "summary": str(data.get("observation") or ""),
                "created": _timestamp(data.get("opened"), path),
                "source": project.relative(path),
                "subject": str(data.get("subject") or ""),
                "instruction": str(data.get("instruction") or data.get("observation") or ""),
                "state": str(data.get("state") or "proposed"),
                "note": str(data.get("decision") or ""),
                "source_row_id": source,
            }
        )
    return rows


def _design_state(value: str) -> str:
    return {
        "accepted": "adopted",
        "adopted": "adopted",
        "rejected": "rejected",
        "closed": "adopted",
    }.get(value, "proposed")


def _change_design_rows(
    project: Project, proposals: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    path = project.path(str(project.config.get("change_designs") or "notebook/designs"))
    rows: list[dict[str, Any]] = []
    values = _read_objects(path)
    if values:
        for index, entry in enumerate(values):
            identifier = str(entry.get("id") or f"CD-{index + 1:04d}")
            rows.append(
                {
                    "id": identifier,
                    "title": str(entry.get("title") or identifier),
                    "summary": str(entry.get("summary") or ""),
                    "created": _timestamp(entry.get("created"), path),
                    "source": project.relative(path),
                    "state": str(entry.get("state") or "proposed"),
                    "findings": _role_links(entry.get("findings"), "motivated_by"),
                    "proposals": _role_links(entry.get("proposals"), "from_proposal"),
                }
            )
        return rows
    for proposal in proposals:
        suffix = proposal["id"].removeprefix("P-")
        rows.append(
            {
                "id": f"CD-{suffix}",
                "title": f"Design from {proposal['source_row_id']}",
                "summary": proposal["instruction"],
                "created": proposal["created"],
                "source": proposal["source"],
                "state": _design_state(proposal["state"]),
                "findings": [],
                "proposals": [(proposal["id"], "from_proposal")],
            }
        )
    return rows


def _role_links(value: Any, default_role: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for item in _list(value):
        if isinstance(item, str):
            links.append((item, default_role))
        elif isinstance(item, dict) and item.get("id"):
            links.append((str(item["id"]), str(item.get("role") or default_role)))
    return links


def _view_files(project: Project) -> dict[str, dict[str, str]]:
    """Map a revision id to the latest captured viewer file for that revision.

    A capture is an artifact written by ``import_snapshot`` when the graph is
    edited. The database does not model it as an entity; the revision event owns
    the view.
    """
    directory = project.snapshots_dir
    views: dict[str, dict[str, str]] = {}
    for meta_path in directory.glob("*.meta.json"):
        meta = _json(meta_path)
        revision = str(meta.get("revision") or "").strip()
        file = str(meta.get("snapshot_file") or "").strip()
        if not revision or not file:
            continue
        path = directory / file
        if not path.is_file():
            continue
        revision_id = revision if revision.startswith("KG-") else f"KG-{revision}"
        saved_at = _timestamp(meta.get("saved_at"), path)
        previous = views.get(revision_id)
        if previous is None or saved_at > previous["saved_at"]:
            views[revision_id] = {
                "file": file,
                "saved_at": saved_at,
                "source": project.relative(path),
            }
    return views


def _event_rows(project: Project) -> list[dict[str, Any]]:
    path = project.path(str(project.config.get("events") or "notebook/records/events"))
    events: list[dict[str, Any]] = []
    for data in _read_objects(path):
        if not data.get("id"):
            continue
        events.append(data)
    return events


def _load_rows(project: Project) -> dict[str, Any]:
    revisions = _revision_rows(project)
    designs = _evaluation_design_rows(project)
    runs, results = _evaluation_rows(project, revisions, designs)
    findings = _finding_rows(project)
    proposals = _proposal_rows(project)
    changes = _change_design_rows(project, proposals)
    return {
        "revision": revisions,
        "evaluation_design": designs,
        "evaluation_run": runs,
        "result": results,
        "finding": findings,
        "proposal": proposals,
        "change_design": changes,
    }


def _link(rows: list[dict[str, Any]], identifier: str, role: str, kind: str) -> dict[str, Any] | None:
    for row in rows:
        if row["id"] == identifier:
            return {"id": identifier, "kind": kind, "title": row["title"], "role": role}
    return None


def _links_for(kind: str, row: dict[str, Any], rows: dict[str, Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []

    def add(target_id: str | None, target_kind: str, role: str) -> None:
        if not target_id:
            return
        link = _link(rows.get(target_kind, []), target_id, role, target_kind)
        if link:
            links.append(link)

    if kind == "revision":
        add(row.get("produced_by"), "change_design", "produced_by")
        for run in rows["evaluation_run"]:
            if run.get("revision_id") == row["id"]:
                add(run["id"], "evaluation_run", "evaluated_by")
    elif kind == "evaluation_design":
        for run in rows["evaluation_run"]:
            if run.get("evaluation_design_id") == row["id"]:
                add(run["id"], "evaluation_run", "tested_by")
    elif kind == "evaluation_run":
        add(row.get("revision_id"), "revision", "on_revision")
        add(row.get("evaluation_design_id"), "evaluation_design", "uses_design")
        for result in rows["result"]:
            if result.get("evaluation_run_id") == row["id"]:
                add(result["id"], "result", "produced_result")
    elif kind == "result":
        add(row.get("evaluation_run_id"), "evaluation_run", "from_run")
        for finding in rows["finding"]:
            if any(item[0] == row["id"] for item in finding.get("results", [])):
                add(finding["id"], "finding", "supports_finding")
    elif kind == "finding":
        for result_id, role in row.get("results", []):
            add(result_id, "result", role)
        for design in rows["change_design"]:
            for finding_id, role in design.get("findings", []):
                if finding_id == row["id"]:
                    add(design["id"], "change_design", role)
    elif kind == "proposal":
        for design in rows["change_design"]:
            for proposal_id, role in design.get("proposals", []):
                if proposal_id == row["id"]:
                    add(design["id"], "change_design", role)
    elif kind == "change_design":
        for finding_id, role in row.get("findings", []):
            add(finding_id, "finding", role)
        for proposal_id, role in row.get("proposals", []):
            add(proposal_id, "proposal", role)
        for revision in rows["revision"]:
            if revision.get("produced_by") == row["id"]:
                add(revision["id"], "revision", "produced")
    return links


def _fields_for(kind: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    if kind == "revision":
        return [
            _field("Version", row.get("version") or "not reported"),
            _field("Manifest", (row.get("manifest") or "")[:12] or "not reported", "code"),
            _field("View", row.get("view_file") or "not captured", "code"),
            *[
                _field(metric["name"].replace("_", " ").title(), _display(metric["value"]) if metric["value"] is not None else metric["value_text"], "metric")
                for metric in row.get("metrics", [])
            ],
        ]
    if kind == "evaluation_design":
        return [_field("Mode", row.get("mode", ""))]
    if kind == "evaluation_run":
        status = str(row.get("status") or "")
        return [_field("Status", status, "pill", "accepted" if status == "passed" else "rejected")]
    if kind == "result":
        fields = [_field("Report", row.get("report") or "not reported", "code")]
        fields.extend(
            _field(metric["name"].replace("_", " ").title(), _display(metric["value"]) if metric["value"] is not None else metric["value_text"], "metric")
            for metric in row.get("metrics", [])
        )
        return fields
    if kind == "finding":
        state = str(row.get("state") or "proposed")
        tone = {"accepted": "accepted", "closed": "accepted", "rejected": "rejected", "proposed": "pending"}.get(state, "neutral")
        return [
            _field("State", state, "pill", tone),
            _field("Layer", row.get("layer") or "unspecified"),
            _field("Decision", row.get("note") or ""),
            _field("Metric", row.get("metric") or "", "metric"),
        ]
    if kind == "proposal":
        state = str(row.get("state") or "proposed")
        tone = "accepted" if state == "accepted" else "rejected" if state == "rejected" else "pending"
        return [
            _field("State", state, "pill", tone),
            _field("Subject", row.get("subject") or ""),
            _field("Instruction", row.get("instruction") or ""),
            _field("Source row", row.get("source_row_id") or "", "code"),
        ]
    if kind == "change_design":
        state = str(row.get("state") or "proposed")
        tone = "accepted" if state == "adopted" else "rejected" if state == "rejected" else "pending"
        return [_field("State", state, "pill", tone)]
    return []


def _synth_events(rows: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in rows["revision"]:
        events.append(
            {
                "id": row["id"],
                "type": "kg_edited",
                "timestamp": row["created"],
                "title": row["title"],
                "entity_id": row["id"],
                "entity_kind": "revision",
                "revision_id": row["id"],
                "view_file": row.get("view_file") or None,
            }
        )
    for row in rows["evaluation_run"]:
        events.append(
            {
                "id": row["id"],
                "type": "evaluation_run",
                "timestamp": row["created"],
                "title": row["title"],
                "entity_id": row["id"],
                "entity_kind": "evaluation_run",
                "revision_id": row.get("revision_id"),
                "evaluation_design_id": row.get("evaluation_design_id"),
            }
        )
    for row in rows["change_design"]:
        events.append(
            {
                "id": row["id"],
                "type": "design_proposed",
                "timestamp": row["created"],
                "title": row["title"],
                "entity_id": row["id"],
                "entity_kind": "change_design",
                "change_design_id": row["id"],
            }
        )
        if row.get("state") == "adopted":
            events.append(
                {
                    "id": f"{row['id']}:adopted",
                    "type": "design_adopted",
                    "timestamp": row["created"],
                    "title": "Design adopted",
                    "entity_id": row["id"],
                    "entity_kind": "change_design",
                    "change_design_id": row["id"],
                }
            )
    return events


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
                }
            )
    return sorted(objects, key=lambda item: (rank.get(item["kind"], 9), item["id"]))


def timeline(project: Project | None = None) -> list[dict[str, Any]]:
    project = project or load_project()
    events = _event_rows(project)
    stored = None
    if not events:
        stored = _load_rows(project)
        events = _synth_events(stored)
    revisions = {
        row["id"]: row
        for row in (stored["revision"] if stored else _revision_rows(project))
    }
    views = _view_files(project)
    rows: list[dict[str, Any]] = []
    for event in events:
        revision_key = str(event.get("revision_id") or event.get("revision") or "")
        if revision_key and not revision_key.startswith("KG-"):
            revision_key = f"KG-{revision_key}"
        captured = views.get(revision_key, {}).get("file") if revision_key else None
        title = event.get("title") or event.get("id")
        message = None
        if event.get("entity_kind") == "revision":
            revision = revisions.get(revision_key) or revisions.get(
                str(event.get("entity_id") or "")
            )
            if revision:
                if revision.get("title"):
                    title = revision["title"]
                message = revision.get("message")
        row = {
            "id": event.get("id"),
            "type": event.get("kind") or event.get("type") or "event",
            "timestamp": event.get("at") or event.get("timestamp") or "",
            "title": title,
            **({"message": message} if message else {}),
            "entity_id": event.get("entity_id"),
            "entity_kind": event.get("entity_kind"),
            "revision_id": event.get("revision_id") or event.get("revision"),
            "evaluation_design_id": event.get("evaluation_design_id"),
            "result_id": event.get("result_id"),
            "change_design_id": event.get("change_design_id"),
            "view_file": event.get("view_file") or captured,
            "prev": list(event.get("prev") or []),
            "temporary": bool(event.get("temporary")),
        }
        rows.append(row)
    return sorted(rows, key=lambda row: (str(row["timestamp"]), str(row["id"])))


def view_file_for(project: Project, revision: str) -> Path | None:
    view = _view_files(project).get(revision)
    if not view:
        return None
    candidate = (project.snapshots_dir / view["file"]).resolve()
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
    }


