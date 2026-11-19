"""Build the static viewer surfaces into the wheel.

The design viewer and the notebook console are separate frontend deliverables.
A wheel build compiles both once with Node, then places their static exports
under ``kg_build_system/viewer_dist`` and ``kg_build_system/console_dist`` so
``kbs view`` and ``kbs console`` run without Node at runtime.

Environment:
    KBS_SKIP_VIEWER_BUILD=1    use the existing ``viewer/design/out``
    KBS_SKIP_CONSOLE_BUILD=1   use the existing ``viewer/console/out``
    KBS_SKIP_VIEWER_INSTALL=1  use existing ``viewer/node_modules``
    KBS_NPM=/path/to/npm       alternate npm executable
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ViewerBuildHook(BuildHookInterface):
    PLUGIN_NAME = "viewer"

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        # Editable installs read the source frontends; only a wheel carries the
        # compiled static exports.
        if version == "editable" or self.target_name != "wheel":
            return

        root = Path(self.root)
        workspace = root / "viewer"
        design = workspace / "design"
        console = workspace / "console"
        design_out = design / "out"
        console_out = console / "out"
        for required in (workspace, design, console):
            if not (required / "package.json").exists():
                raise RuntimeError(f"{required.relative_to(root)}/package.json is missing")

        build_viewer = os.environ.get("KBS_SKIP_VIEWER_BUILD") != "1"
        build_console = os.environ.get("KBS_SKIP_CONSOLE_BUILD") != "1"
        if build_viewer or build_console:
            npm = os.environ.get("KBS_NPM") or shutil.which("npm")
            if not npm:
                raise RuntimeError(
                    "npm is required to build the bundled frontends; install Node "
                    "or set KBS_NPM, or set KBS_SKIP_VIEWER_BUILD=1 and "
                    "KBS_SKIP_CONSOLE_BUILD=1 with existing out directories"
                )
            if os.environ.get("KBS_SKIP_VIEWER_INSTALL") != "1":
                subprocess.run([npm, "ci"], cwd=workspace, check=True)
            environment = {
                **os.environ,
                "NEXT_TELEMETRY_DISABLED": "1",
                "CI": "1",
            }
            if build_viewer:
                if design_out.exists():
                    shutil.rmtree(design_out)
                subprocess.run(
                    [npm, "run", "build:static", "--workspace", "design"],
                    cwd=workspace,
                    check=True,
                    env={**environment, "KBS_VIEWER_STATIC": "1"},
                )
            if build_console:
                if console_out.exists():
                    shutil.rmtree(console_out)
                subprocess.run(
                    [npm, "run", "build:static", "--workspace", "console"],
                    cwd=workspace,
                    check=True,
                    env={**environment, "KBS_CONSOLE_STATIC": "1"},
                )

        for name, out in (("design viewer", design_out), ("console", console_out)):
            if not (out / "index.html").exists():
                raise RuntimeError(
                    f"{name} export is missing at {out}; run its static build"
                )

        self._temp = tempfile.TemporaryDirectory(prefix="kbs-frontends-")
        temporary = Path(self._temp.name)
        for name, out in (("viewer_dist", design_out), ("console_dist", console_out)):
            target = temporary / name
            # Project snapshots are served by the Python servers; demo data is
            # not part of the package.
            shutil.copytree(out, target, ignore=shutil.ignore_patterns("data"))
            build_data["force_include"][str(target)] = f"kg_build_system/{name}"

    def finalize(
        self,
        version: str,
        build_data: dict[str, object],
        artifact_path: str,
    ) -> None:
        temp = getattr(self, "_temp", None)
        if temp is not None:
            temp.cleanup()
            self._temp = None
