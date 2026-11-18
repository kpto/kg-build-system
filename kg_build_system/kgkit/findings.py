"""Add a finding to the ledger and its event to the chain.

A finding is added once. The ledger validates the record; the event records the
addition in the iteration chain. A later interpretation is a new finding or a
design decision, not a state change on the old row.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import events, ledger
from .config import Project


def findings_dir(project: Project) -> Path:
    return project.path(str(project.config.get("findings") or "kgkit/records/findings"))


def list_findings(project: Project) -> tuple[list[dict[str, Any]], list[str]]:
    path = findings_dir(project)
    if not path.exists():
        return [], []
    return ledger.read_ledger(path)


def add(
    project: Project,
    *,
    layer: str,
    observation: str,
    evidence: Any,
    decision: str,
    metric: Any,
) -> dict[str, Any]:
    path = findings_dir(project)
    rows, _errors = ledger.read_ledger(path) if path.exists() else ([], [])
    row: dict[str, Any] = {
        "id": ledger.next_id(rows),
        "opened": datetime.now(UTC).isoformat(timespec="seconds"),
        "layer": layer,
        "observation": observation,
        "evidence": evidence,
        "decision": decision,
        "metric": metric,
    }
    result = ledger.append_finding(path, row)
    if result["status"] != "accepted":
        raise ValueError("; ".join(result["errors"]))
    event = events.append(
        project,
        "finding_added",
        [{"kind": "finding", "id": row["id"]}],
        {"finding": row},
    )
    row["last_event"] = event["id"]
    target = path / f"{row['id']}.json"
    if target.is_file():
        target.write_text(
            json.dumps(row, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    return row


__all__ = ["add", "findings_dir", "list_findings"]
