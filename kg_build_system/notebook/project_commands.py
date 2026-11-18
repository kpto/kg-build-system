"""Run project-defined commands from ``notebook/config.json``.

The package owns the generic surface: relations, snapshots, the console and the
ledger. A project owns how its graph is validated, built, audited and
evaluated. ``commands`` maps a name to one shell command; the command must
print one JSON object and return a non-zero exit code when it fails.

The project workspace (``<project>/notebook``) is prepended to ``PYTHONPATH`` so a
project can keep its operations in ``notebook/ops`` and its evaluation in
``notebook/eval`` without packaging either as an application.

Example:
    ```json
    {
      "commands": {
        "status": "uv run python -m ops.commands status --json",
        "eval": "uv run python -m ops.commands eval {mode} --json"
      }
    }
    ```
"""

from __future__ import annotations

import os

import json
import shlex
import subprocess
from typing import Any

from .config import Project


def command(project: Project, name: str) -> str | None:
    """Return the configured command template for ``name``, if any."""

    commands = project.config.get("commands")
    if not isinstance(commands, dict):
        return None
    value = commands.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _workspace_env(project: Project) -> dict[str, str]:
    """Run project commands with the workspace importable as a package root."""

    env = os.environ.copy()
    workspace = str(project.data_dir)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = workspace if not existing else workspace + os.pathsep + existing
    return env


def run(project: Project, name: str, **parameters: object) -> dict[str, Any]:
    """Run one configured command and parse its JSON object.

    Placeholders are substituted with shell-quoted values. A missing command is
    not an exception: it returns ``ok: false`` with a fixable message, so the
    CLI and the console can render the reason.
    """

    template = command(project, name)
    if template is None:
        return {
            "ok": False,
            "error": (
                f"no commands.{name} in {project.config_path}; add one to run "
                f"this project operation"
            ),
        }
    values = {
        key: shlex.quote(str(value)) for key, value in parameters.items()
    }
    values["root"] = shlex.quote(str(project.root))
    try:
        rendered = template.format(**values)
    except KeyError as exc:
        return {
            "ok": False,
            "error": f"commands.{name} has an unknown placeholder: {exc}",
        }
    completed = subprocess.run(
        rendered,
        shell=True,
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
        env=_workspace_env(project),
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    data: dict[str, Any] | None = None
    if stdout:
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            data = None
    if data is None:
        return {
            "ok": False,
            "command": rendered,
            "exit_code": completed.returncode,
            "error": stderr or stdout or f"commands.{name} printed no JSON",
        }
    data.setdefault("ok", completed.returncode == 0)
    data["command"] = rendered
    data["exit_code"] = completed.returncode
    if stderr:
        data["stderr"] = stderr
    return data


__all__ = ["command", "run"]
