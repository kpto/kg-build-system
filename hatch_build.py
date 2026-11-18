"""Build the static viewer into the wheel.

The viewer is a separate frontend deliverable. A wheel build compiles it once
with Node, then places the static export under ``kg_build_system/viewer_dist``
so ``kbs view`` can serve it without Node at runtime.

Environment:
    KBS_SKIP_VIEWER_BUILD=1   use the existing ``viewer/design/out``
    KBS_SKIP_VIEWER_INSTALL=1 use existing ``viewer/design/node_modules``
    KBS_NPM=/path/to/npm      alternate npm executable
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
        # Editable installs read the source viewer; only a wheel carries the
        # compiled static export.
        if version == "editable" or self.target_name != "wheel":
            return

        root = Path(self.root)
        viewer = root / "viewer" / "design"
        out = viewer / "out"
        if not (viewer / "package.json").exists():
            raise RuntimeError("viewer/design/package.json is missing")

        if os.environ.get("KBS_SKIP_VIEWER_BUILD") != "1":
            npm = os.environ.get("KBS_NPM") or shutil.which("npm")
            if not npm:
                raise RuntimeError(
                    "npm is required to build the bundled viewer; install Node "
                    "or set KBS_NPM, or set KBS_SKIP_VIEWER_BUILD=1 with an "
                    "existing viewer/design/out"
                )
            if os.environ.get("KBS_SKIP_VIEWER_INSTALL") != "1":
                subprocess.run([npm, "ci"], cwd=viewer, check=True)
            if out.exists():
                shutil.rmtree(out)
            subprocess.run(
                [npm, "run", "build:static"],
                cwd=viewer,
                check=True,
                env={
                    **os.environ,
                    "KBS_VIEWER_STATIC": "1",
                    "NEXT_TELEMETRY_DISABLED": "1",
                    "CI": "1",
                },
            )

        if not (out / "index.html").exists():
            raise RuntimeError(
                "viewer/design/out/index.html is missing; run the static viewer build"
            )

        self._temp = tempfile.TemporaryDirectory(prefix="kbs-viewer-")
        target = Path(self._temp.name) / "viewer_dist"
        # Project snapshots are served by ``kbs view``; demo data is not part
        # of the package.
        shutil.copytree(
            out,
            target,
            ignore=shutil.ignore_patterns("data"),
        )
        build_data["force_include"][str(target)] = "kg_build_system/viewer_dist"

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
