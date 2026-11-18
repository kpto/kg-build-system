"""The append-only findings ledger.

A finding is added once: it records an observation, the evidence that supports
it, and the decision it motivates. There is no finding state machine and no
proposal layer; a later interpretation is a new finding or a design decision.

The ledger is one JSON object per line, or one object per file in a directory.
These functions do not print and do not parse arguments; the CLI and the console
call them directly.

Example:
    ```python
    from kg_build_system.kgkit.ledger import append_finding

    result = append_finding(Path("kgkit/records/findings"), row)
    assert result["status"] == "accepted"
    ```
"""

from __future__ import annotations

import datetime as _datetime
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

REQUIRED_FIELDS = (
    "id",
    "opened",
    "layer",
    "observation",
    "evidence",
    "decision",
    "metric",
)


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_opened(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    try:
        if "T" in text:
            _datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            _datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def validate_finding(
    row: Mapping[str, Any],
    *,
    existing_ids: Sequence[str] | None = None,
) -> list[str]:
    """Return a list of validation errors; an empty list means valid."""

    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"missing field: {field}")
    if errors:
        return errors
    if not _non_empty_text(row.get("id")):
        errors.append("id must be a non-empty string")
    elif existing_ids and str(row["id"]) in set(existing_ids):
        errors.append(f"duplicate id: {row['id']}")
    if not _valid_opened(row.get("opened")):
        errors.append("opened must be an ISO date (YYYY-MM-DD) or datetime")
    if not _non_empty_text(row.get("layer")):
        errors.append("layer must be a non-empty string")
    if not _non_empty_text(row.get("observation")):
        errors.append("observation must be a non-empty string")
    if not _non_empty_text(row.get("decision")):
        errors.append("decision must be a non-empty string")
    evidence = row.get("evidence")
    if (
        evidence is None
        or (isinstance(evidence, str) and not evidence.strip())
        or (isinstance(evidence, (list, tuple, dict)) and len(evidence) == 0)
    ):
        errors.append("evidence must be non-empty")
    metric = row.get("metric")
    if not isinstance(metric, (str, int, float, list, tuple, dict)) and metric is not None:
        errors.append("metric must be a string, number, list, object or null")
    return errors


def read_ledger(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, [f"missing input: {path.name}"]
    if path.is_dir():
        for item in sorted(path.glob("*.json")):
            try:
                value = json.loads(item.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{item.name}: {exc}")
                continue
            if not isinstance(value, Mapping):
                errors.append(f"{item.name}: row is not an object")
                continue
            row = dict(value)
            row_errors = validate_finding(row)
            if row_errors:
                errors.extend(f"{item.name}: {message}" for message in row_errors)
            rows.append(row)
        return rows, errors
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{lineno}: {exc.msg}")
                continue
            if not isinstance(value, Mapping):
                errors.append(f"{path.name}:{lineno}: row is not an object")
                continue
            row = dict(value)
            row_errors = validate_finding(row)
            if row_errors:
                errors.extend(f"{path.name}:{lineno}: {message}" for message in row_errors)
            rows.append(row)
    seen: set[str] = set()
    for row in rows:
        identifier = row.get("id")
        if isinstance(identifier, str):
            if identifier in seen:
                errors.append(f"{path.name}: duplicate id: {identifier}")
            seen.add(identifier)
    return rows, errors


def validate_ledger(path: Path) -> dict[str, Any]:
    rows, errors = read_ledger(path)
    by_layer: dict[str, int] = {}
    for row in rows:
        layer = str(row.get("layer") or "unspecified")
        by_layer[layer] = by_layer.get(layer, 0) + 1
    return {
        "status": "passed" if not errors else "failed",
        "rows": len(rows),
        "by_layer": by_layer,
        "errors": errors,
    }


def next_id(rows: Sequence[Mapping[str, Any]], prefix: str = "F") -> str:
    """Return the next unused identifier in the ``<prefix>-0001`` form."""

    used: set[int] = set()
    for row in rows:
        identifier = str(row.get("id") or "")
        if not identifier.startswith(f"{prefix}-"):
            continue
        suffix = identifier[len(prefix) + 1 :]
        if suffix.isdigit():
            used.add(int(suffix))
    return f"{prefix}-{max(used, default=0) + 1:04d}"


def append_finding(
    path: Path,
    row: Mapping[str, Any],
    *,
    existing_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate and append one row. Nothing is written when validation fails."""

    rows, read_errors = read_ledger(path) if path.exists() else ([], [])
    ids = list(existing_ids or [])
    ids.extend(str(item["id"]) for item in rows if isinstance(item.get("id"), str))
    candidate = dict(row)
    errors = validate_finding(candidate, existing_ids=ids)
    if errors:
        return {
            "status": "rejected",
            "errors": errors + (read_errors if path.exists() else []),
            "row": candidate,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir() or path.suffix == "":
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{candidate['id']}.json").write_text(
            json.dumps(candidate, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        line = json.dumps(candidate, sort_keys=True, ensure_ascii=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return {"status": "accepted", "errors": [], "row": candidate}


__all__ = [
    "REQUIRED_FIELDS",
    "append_finding",
    "next_id",
    "read_ledger",
    "validate_finding",
    "validate_ledger",
]
