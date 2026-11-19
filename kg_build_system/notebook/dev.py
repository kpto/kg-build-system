"""Per-user development process registry.

The console, the design viewer and the API can run as three separate dev
servers. Each one binds an available port and writes its URL under a role file;
the others read those files instead of being given a port.

The registry is a directory, not one shared document, so two roles never
overwrite each other.  A role file carries the URL and the writing process id;
a caller health-checks the URL before using it.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROLES = ("api", "console", "viewer")


def dev_dir() -> Path:
    """The per-user directory for development role files."""

    override = os.environ.get("KBS_DEV_DIR")
    if override:
        return Path(override).expanduser()
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        return base / "kbs" / "dev"
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "kbs" / "dev"
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime) / "kbs" / "dev"
    return home / ".cache" / "kbs" / "dev"


def role_path(role: str) -> Path:
    if role not in ROLES:
        raise ValueError(f"unknown dev role {role!r}")
    return dev_dir() / f"{role}.json"


def read_role(role: str) -> dict[str, Any]:
    path = role_path(role)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def read_roles() -> dict[str, dict[str, Any]]:
    return {role: value for role in ROLES if (value := read_role(role))}


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    os.replace(temporary, path)


def write_role(role: str, url: str) -> dict[str, Any]:
    """Publish one role URL, replacing any previous entry for that role."""

    value = {
        "url": url.rstrip("/"),
        "pid": os.getpid(),
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    _write_atomic(role_path(role), value)
    return value


def remove_role(role: str) -> None:
    """Remove a role entry if this process wrote it or it is already gone."""

    path = role_path(role)
    entry = read_role(role)
    if entry and entry.get("pid") not in (None, os.getpid()):
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return


__all__ = [
    "ROLES",
    "dev_dir",
    "read_role",
    "read_roles",
    "remove_role",
    "role_path",
    "write_role",
]
