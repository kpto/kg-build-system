"""Compile Open Targets and write a viewer snapshot without executing it.

This is the compile worker for the viewer's live/event-based mode. It imports
the project, builds the blueprint and workflow plan only, then serialises the
framework documents directly. No parquet data is read and no artifact is
published.

Run inside the Open Targets project environment:

    cd ~/Repos/opentargets-kg
    uv run python /home/paul/Repos/kg-build-system/viewer/scripts/compile_opentargets_snapshot.py

The workflow plan carries the source blueprint document in its provenance, so
the output has no separate blueprint artifact. The output is deterministic for
the same source tree. It intentionally omits the meta graph and build report
because those describe a previous execution, not the current compile. The viewer
labels the result as compile-only.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from kg_build_system.kernel.service._private.workflow_codec import (
    workflow_plan_to_document,
)
from open_targets_kg.manifest import compile_kg, create_kg_blueprint


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
        "--title",
        default="Open Targets 26.09 Knowledge Graph (compiled)",
    )
    args = parser.parse_args()

    blueprint = create_kg_blueprint()
    plan = compile_kg(blueprint)
    workflow_document = workflow_plan_to_document(plan)
    provenance = plan.provenance
    if not isinstance(provenance, dict) or not isinstance(
        provenance.get("blueprint"), dict
    ):
        raise RuntimeError(
            "compiled plan does not carry its source blueprint in provenance"
        )
    blueprint_document = provenance["blueprint"]

    # The workflow document is the only source. Its provenance carries the
    # blueprint, so the viewer does not need a second artifact.
    snapshot = {
        "format": "kg-viewer-snapshot",
        "version": 1,
        "name": "open-targets-26.09",
        "title": args.title,
        "workflow": workflow_document,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False)
    args.output.write_text(payload, encoding="utf-8")
    gzip_path = args.output.with_suffix(args.output.suffix + ".gz")
    # mtime=0 keeps the gzip bytes deterministic for the same source tree.
    with gzip_path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0
        ) as stream:
            stream.write(payload.encode("utf-8"))

    graph = blueprint_document["graph"]
    data = blueprint_document["data"]
    result = {
        "snapshot": str(args.output),
        "bytes": args.output.stat().st_size,
        "gzip": str(gzip_path),
        "gzip_bytes": gzip_path.stat().st_size,
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "source_relations": len(data["source_relations"]),
        "derived_relations": len(data["derived_relations"]),
        "bindings": len(blueprint_document["bindings"]),
        "steps": len(workflow_document["steps"]),
        "connections": len(workflow_document["connections"]),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
