"""Evaluation records added to the notebook.

An evaluation is one run of a project-owned evaluation mode over the current
compilation. The package records the status, the metrics and the report path; it
does not run the project's tests. ``kbs notebook eval`` runs the project command
and then calls ``add`` with the report it wrote.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from . import events
from .config import Project


def evaluations_dir(project: Project) -> Path:
    return project.path(str(project.config.get("evaluations") or "kgkit/records/evaluations"))


def read_evaluations(project: Project) -> list[dict[str, Any]]:
    directory = evaluations_dir(project)
    if not directory.is_dir():
        return []
    values: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("id"):
            values.append(value)
    return values


def read_evaluation(project: Project, identifier: str) -> dict[str, Any] | None:
    for evaluation in read_evaluations(project):
        if evaluation.get("id") == identifier:
            return evaluation
    return None


def latest(project: Project) -> dict[str, Any] | None:
    values = read_evaluations(project)
    if not values:
        return None
    return sorted(values, key=lambda item: (str(item.get("created") or ""), str(item["id"])))[-1]


def next_id(project: Project) -> str:
    used: list[int] = []
    for evaluation in read_evaluations(project):
        suffix = str(evaluation.get("id") or "").removeprefix("EV-")
        if suffix.isdigit():
            used.append(int(suffix))
    return f"EV-{max(used, default=0) + 1:04d}"


def _suite_status(suites: dict[str, Any]) -> str:
    statuses = [str(value.get("status") or "") for value in suites.values() if isinstance(value, dict)]
    if "failed" in statuses:
        return "failed"
    if "passed" in statuses:
        return "passed"
    if statuses and all(status == "skipped" for status in statuses):
        return "skipped"
    return "unknown"


def _report_metrics(report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    suites = report.get("suites")
    suites = suites if isinstance(suites, dict) else {}
    pairs: list[tuple[str, Any]] = []
    for name, key in (
        ("suites_passed", "passed"),
        ("suites_total", "suites"),
        ("suites_failed", "failed"),
        ("suites_skipped", "skipped"),
    ):
        if summary.get(key) is not None:
            pairs.append((name, summary.get(key)))
    audit = suites.get("audit")
    audit = audit if isinstance(audit, dict) else {}
    metrics = audit.get("metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    for name, key in (
        ("nodes", "node_count"),
        ("edges", "edge_count"),
        ("evidence_rows", "record_count"),
    ):
        if metrics.get(key) is not None:
            pairs.append((name, metrics.get(key)))
    rows: list[dict[str, Any]] = []
    for name, value in pairs:
        rows.append(
            {
                "name": name,
                "value": float(value) if isinstance(value, (int, float)) else None,
                "value_text": None if isinstance(value, (int, float)) else str(value),
            }
        )
    return rows


def add(
    project: Project,
    *,
    report: str | Path | None = None,
    mode: str | None = None,
    status: str | None = None,
    metrics: Iterable[dict[str, Any]] = (),
    revision: str | None = None,
    design: str | None = None,
) -> dict[str, Any]:
    """Append one evaluation record and its ``evaluation_added`` event."""

    report_path = project.path(report) if report else None
    payload: dict[str, Any] = {}
    if report_path is not None:
        if not report_path.is_file():
            raise FileNotFoundError(f"evaluation report not found: {report_path}")
        value = json.loads(report_path.read_text(encoding="utf-8"))
        payload = value if isinstance(value, dict) else {}
    summary = payload.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    suites = payload.get("suites")
    suites = suites if isinstance(suites, dict) else {}
    resolved_status = str(status or summary.get("status") or _suite_status(suites))
    resolved_mode = str(mode or payload.get("mode") or (report_path.stem if report_path else "evaluation"))
    resolved_metrics = _report_metrics(payload) if payload else list(metrics)
    revision_info = payload.get("revision")
    revision_info = revision_info if isinstance(revision_info, dict) else {}
    resolved_revision = str(
        revision
        or revision_info.get("revision")
        or revision_info.get("blueprint_fingerprint")
        or ""
    )
    evaluation = {
        "id": next_id(project),
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": resolved_mode,
        "status": resolved_status,
        "metrics": resolved_metrics,
        "report": project.relative(report_path) if report_path else "",
        "revision_id": resolved_revision if resolved_revision.startswith("KG-") else "",
        "fingerprint": "" if resolved_revision.startswith("KG-") else resolved_revision,
        "design_id": str(design or resolved_mode),
    }
    refs = [{"kind": "evaluation", "id": evaluation["id"]}]
    if evaluation["revision_id"]:
        refs.append({"kind": "revision", "id": evaluation["revision_id"]})
    event = events.append(project, "evaluation_added", refs, {"evaluation": evaluation})
    evaluation["last_event"] = event["id"]
    directory = evaluations_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{evaluation['id']}.json").write_text(
        json.dumps(evaluation, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return evaluation


__all__ = [
    "add",
    "evaluations_dir",
    "latest",
    "next_id",
    "read_evaluation",
    "read_evaluations",
]
