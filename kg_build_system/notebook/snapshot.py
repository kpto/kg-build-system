"""Write and import a compiled viewer snapshot.

The package does not know how a project builds its graph. It owns the snapshot
format: it can wrap a workflow document into ``kg-viewer-snapshot`` and write the
current file plus a timestamped archive, and it can import a snapshot the project
produced into ``notebook/records/views``. There is no database.
"""

from __future__ import annotations

import gzip
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Project, find_snapshot_source, load_project


def _read_json(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def _is_snapshot(value: dict[str, Any]) -> bool:
    if value.get("format") == "kg-viewer-snapshot":
        return True
    if isinstance(value.get("blueprint"), dict) and isinstance(value.get("workflow"), dict):
        return True
    if any(key in value for key in ("steps", "connections", "components")):
        return True
    return any(key in value for key in ("graph", "data", "bindings", "assets"))


def _slug(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "-" for char in value).strip("-")
    return cleaned or "snapshot"


def _snapshot_revision(value: dict[str, Any]) -> str:
    direct = value.get("revision")
    if isinstance(direct, str) and direct:
        return direct
    workflow = value.get("workflow")
    if isinstance(workflow, dict):
        provenance = workflow.get("provenance")
        if isinstance(provenance, dict):
            revision = provenance.get("revision")
            if isinstance(revision, str) and revision:
                return revision
    return ""


def import_snapshot(
    project: Project | None = None,
    *,
    source: str | Path | None = None,
    command: str | None = None,
    revision: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    project = project or load_project()
    project.ensure()
    if command:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=project.root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip()
                or completed.stdout.strip()
                or f"snapshot command exited with {completed.returncode}"
            )
    source_path = project.path(source) if source else find_snapshot_source(project)
    if source_path is None or not source_path.is_file():
        raise FileNotFoundError(
            "no snapshot source found; pass --from <file> or set snapshot_command "
            "in notebook/config.json"
        )
    payload = _read_json(source_path)
    if not _is_snapshot(payload):
        raise ValueError(
            f"{source_path} is not a viewer snapshot, workflow plan or blueprint"
        )

    saved_at = datetime.now(UTC)
    resolved_revision = (revision or _snapshot_revision(payload)).strip()
    stem = f"snapshot-{_slug(resolved_revision) if resolved_revision else 'current'}-{saved_at.strftime('%Y%m%dT%H%M%S%fZ')}"
    current = project.snapshots_dir / "current.snapshot.json"
    archive = project.snapshots_dir / f"{stem}.snapshot.json"
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    current.write_text(body, encoding="utf-8")
    archive.write_text(body, encoding="utf-8")
    meta = {
        "saved_at": saved_at.isoformat(timespec="seconds"),
        "revision": resolved_revision,
        "source": project.relative(source_path),
        "title": title or str(payload.get("title") or "Saved snapshot"),
        "summary": "A saved viewer snapshot of the compiled graph.",
        "snapshot_file": archive.name,
    }
    (project.snapshots_dir / "current.meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (project.snapshots_dir / f"{stem}.meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    return {
        "ok": True,
        "project": project.name,
        "data_dir": str(project.data_dir),
        "snapshot": str(current),
        "snapshot_file": current.name,
        "snapshot_history": str(archive),
        "history_file": archive.name,
        "saved_at": saved_at.isoformat(timespec="seconds"),
        "revision": resolved_revision,
        "source": project.relative(source_path),
    }


def write_snapshot_document(
    directory: Path | str,
    *,
    name: str,
    title: str,
    workflow: dict[str, Any],
    revision: str = "",
    stem: str = "current",
) -> dict[str, Any]:
    """Wrap a compiled workflow document and write the current file and archive."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    document = {
        "format": "kg-viewer-snapshot",
        "version": 1,
        "name": name,
        "title": title,
        "workflow": workflow,
    }
    payload = json.dumps(document, separators=(",", ":"), ensure_ascii=False)
    saved_at = datetime.now(UTC)
    path = target / f"{stem}.snapshot.json"
    path.write_text(payload, encoding="utf-8")
    with path.with_suffix(".json.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as handle:
            handle.write(payload.encode())
    resolved = revision or _snapshot_revision(document)
    archive_name = f"{stem}-{resolved or 'current'}-{saved_at.strftime('%Y%m%dT%H%M%S%fZ')}.snapshot.json"
    archive = target / archive_name
    archive.write_text(payload, encoding="utf-8")
    return {
        "snapshot": str(path),
        "snapshot_file": path.name,
        "snapshot_history": str(archive),
        "saved_at": saved_at.isoformat(timespec="seconds"),
        "revision": resolved,
    }


__all__ = ["import_snapshot", "write_snapshot_document"]
