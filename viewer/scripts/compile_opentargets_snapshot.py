"""Compile Open Targets and write a viewer snapshot without executing it.

This is the compile worker for the viewer's live/event-based mode. It imports
the project, builds the blueprint and workflow plan only, then serialises the
framework documents directly. No parquet data is read and no artifact is
published.

Run inside the Open Targets project environment:

    cd ~/Repos/opentargets-kg
    uv run python /home/paul/Repos/kg-build-system/viewer/scripts/compile_opentargets_snapshot.py

The output is deterministic for the same source tree. It intentionally omits
the meta graph and build report because those describe a previous execution,
not the current compile. The viewer labels the result as compile-only.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

from kg_build_system.distribution.interpreter.service.internal import (
    blueprint_to_document,
)
from kg_build_system.kernel.service._private.workflow_codec import (
    workflow_plan_to_document,
)
from open_targets_kg.build import compile_kg, create_kg_blueprint


def read_optional(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build_review(project: Path) -> dict[str, Any]:
    semantics = read_optional(project / "open_targets_kg" / "build" / "semantics.json")
    release = semantics.get("release") if isinstance(semantics, dict) else None
    description = semantics.get("description") if isinstance(semantics, dict) else None
    coverage = semantics.get("coverage") if isinstance(semantics, dict) else None
    parts = []
    if release:
        parts.append(f"Release {release}.")
    if isinstance(description, str) and description:
        parts.append(description)
    if isinstance(coverage, dict):
        components = coverage.get("components")
        bindings = coverage.get("bindings")
        properties = coverage.get("properties")
        if components is not None:
            parts.append(
                f"Coverage: {components} components, {bindings} bindings and {properties} properties."
            )
    return {
        "format": "kg-viewer-review",
        "version": 1,
        "ai": {
            "note": "This is a compile-only snapshot. No model, prompt, run identity or confidence was captured. The meta graph and build report are intentionally absent because they describe a previous execution, not this compile."
        },
        "decisions": [
            {
                "id": "compile-only",
                "title": "The viewer is showing a compile-only snapshot",
                "status": "accepted",
                "rationale": "The blueprint and workflow contract come from the current project source. The graph was not executed, so observed record counts, nullability observations and published artifacts are absent.",
                "subject": {"kind": "asset", "name": "open_target", "component": "open_target"},
                "evidence": [
                    {
                        "label": "compiled workflow provenance",
                        "artifact": "workflow",
                        "jsonPointer": "/provenance",
                    }
                ],
                "tags": ["compile", "provenance", "limits"],
            },
            {
                "id": "open-targets-release",
                "title": f"Open Targets Platform release {release or 'unknown'}",
                "status": "accepted",
                "rationale": " ".join(parts)
                or "The release metadata is not available in this project.",
                "subject": {"kind": "asset", "name": "open_target", "component": "open_target"},
                "evidence": [
                    {
                        "label": "asset semantics",
                        "artifact": "blueprint",
                        "jsonPointer": "/assets/0/semantics",
                    }
                ],
                "tags": ["release", "semantics"],
            },
        ],
        "notes": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Open Targets project root (defaults to the current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="viewer snapshot JSON path",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=None,
        help="review sidecar path; defaults beside the snapshot",
    )
    parser.add_argument(
        "--title",
        default="Open Targets 26.09 Knowledge Graph (compiled)",
    )
    args = parser.parse_args()

    blueprint = create_kg_blueprint()
    plan = compile_kg(blueprint)
    blueprint_document = blueprint_to_document(blueprint)
    workflow_document = workflow_plan_to_document(plan)

    snapshot = {
        "format": "kg-viewer-snapshot",
        "version": 1,
        "name": "open-targets-26.09",
        "title": args.title,
        "blueprint": blueprint_document,
        "workflow": workflow_document,
        "report": {
            "published_artifacts": [],
            "recovered_failures": [],
            "unresolved_failures": [],
            "provenance": {"mode": "compile-only"},
        },
    }
    review = build_review(args.project)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False)
    args.output.write_text(payload, encoding="utf-8")
    gzip_path = args.output.with_suffix(args.output.suffix + ".gz")
    with gzip.open(gzip_path, "wb", compresslevel=9) as stream:
        stream.write(payload.encode("utf-8"))

    review_output = args.review_output or args.output.with_name(
        args.output.name.replace(".snapshot.json", ".review.json")
    )
    review_output.write_text(
        json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "snapshot": str(args.output),
                "bytes": args.output.stat().st_size,
                "gzip": str(gzip_path),
                "gzip_bytes": gzip_path.stat().st_size,
                "review": str(review_output),
                "nodes": len(blueprint_document["graph"]["nodes"]),
                "edges": len(blueprint_document["graph"]["edges"]),
                "relations": len(blueprint_document["data"]["relations"]),
                "projections": len(blueprint_document["data"]["projections"]),
                "bindings": len(blueprint_document["bindings"]),
                "steps": len(workflow_document["steps"]),
                "connections": len(workflow_document["connections"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
