"""Project discovery and the package's per-project data directory.

Every runtime artifact this package writes lives under ``<project>/kgkit``:
snapshots and the project config. The
project keeps owning its own source, build and evaluation files; the package
only reads them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR_NAME = "kgkit"

DEFAULT_CONFIG: dict[str, Any] = {
    "project": "",
    "revisions": "kgkit/records/revisions",
    "events": "kgkit/records/events",
    "findings": "kgkit/records/findings",
    "change_designs": "kgkit/records/designs",
    "evaluations": "kgkit/records/evaluations",
    "documents": "kgkit/records/documents",
    "views": "kgkit/records/views",
    "eval_design": "kgkit/eval/design.json",
    "evaluation_reports": ["kgkit/eval/report.json", "kgkit/eval/quick.json"],
    "snapshot_sources": [
        "build/workflow_plan.json",
        "data/snapshots/current.snapshot.json",
        "viewer/public/data/current.snapshot.json",
        "data/build/workflow_plan.json",
    ],
    "snapshot_command": "",
    "commands": {},
    "viewer_url": "http://127.0.0.1:3000/?embed=1",
    "console_port": 8787,
    "viewer_port": 3000,
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _merge(defaults: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    merged.update(value)
    return merged


@dataclass(frozen=True)
class Project:
    """One knowledge graph project and its private ``kgkit`` data."""

    root: Path
    config: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.config.get("project") or self.root.name)

    @property
    def data_dir(self) -> Path:
        return self.root / DATA_DIR_NAME

    @property
    def snapshots_dir(self) -> Path:
        configured = self.path(str(self.config.get("views") or "kgkit/records/views"))
        if configured.exists():
            return configured
        legacy = self.data_dir / "views"
        return legacy if legacy.exists() else configured

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    def path(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    def paths(self, value: Any) -> list[Path]:
        if isinstance(value, str):
            return [self.path(value)]
        if isinstance(value, list):
            return [self.path(item) for item in value if isinstance(item, str)]
        return []

    def relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def ensure(self, *, write_config: bool = False) -> "Project":
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "records").mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        for key in ("events", "revisions", "findings", "change_designs", "evaluations", "documents"):
            self.path(str(self.config.get(key) or f"kgkit/records/{key}")).mkdir(parents=True, exist_ok=True)
        if write_config and not self.config_path.exists():
            write_config_file(self)
        return self


def load_project(root: str | Path | None = None) -> Project:
    resolved = Path(root or Path.cwd()).expanduser().resolve()
    data_dir = resolved / DATA_DIR_NAME
    config = _merge(DEFAULT_CONFIG, _read_json(data_dir / "config.json"))
    if not config.get("project"):
        config["project"] = resolved.name
    return Project(root=resolved, config=config)


def write_config_file(project: Project) -> dict[str, Any]:
    project.ensure()
    config = _merge(DEFAULT_CONFIG, project.config)
    config["project"] = config.get("project") or project.root.name
    project.config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return config


def find_snapshot_source(project: Project) -> Path | None:
    """Find the project artifact that can become the current viewer snapshot."""

    for path in project.paths(project.config.get("snapshot_sources")):
        if path.is_file():
            return path
    for directory in ("data/snapshots", "viewer/public/data"):
        candidate = project.path(directory)
        if not candidate.is_dir():
            continue
        files = sorted(
            candidate.glob("*.snapshot.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if files:
            return files[0]
    return None


__all__ = [
    "DATA_DIR_NAME",
    "DEFAULT_CONFIG",
    "Project",
    "find_snapshot_source",
    "load_project",
    "write_config_file",
]
