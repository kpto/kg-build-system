"""Build a viewer snapshot from the Open Targets KG build artifacts.

The Open Targets build emits a workflow *contract* (contributions, string
connections and variables) and a blueprint inside its compile provenance. The
viewer consumes the flattened snapshot shape used by ``kg-viewer-snapshot``.
This script performs that translation without executing the graph.

Usage:

    python viewer/scripts/build_opentargets_snapshot.py \
        --project ~/Repos/opentargets-kg \
        --output viewer/public/data/opentargets.snapshot.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ASSET_NAME = "open_target"
ASSET_LOCATOR = "/home/paul/data/otp-26.09/output"
SQL_PREVIEW_LIMIT = 4000

MODULE_ENGINES = {
    "core": "duckdb",
    "collapse_exact_duplicates": "default",
    "file": "default",
    "meta_graph": "default",
    "neo4j": "default",
    "semantics": "default",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def annotation(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    identifier = value.get("annotation_id") or value.get("id")
    if not isinstance(identifier, str):
        return None
    arguments = value.get("arguments")
    return {
        "namespace": str(value.get("namespace", "")),
        "id": identifier,
        "arguments": arguments if isinstance(arguments, dict) else {},
    }


def annotations(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [entry for entry in (annotation(value) for value in values) if entry]


def annotation_argument(
    values: Any,
    key: str,
) -> str | None:
    for entry in annotations(values):
        arguments = entry.get("arguments") or {}
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def expression(value: Any) -> Any:
    """Translate an inline OT expression into the viewer's typed-ref shape."""
    if isinstance(value, list):
        return [expression(entry) for entry in value]
    if not isinstance(value, dict):
        return value

    result = dict(value)
    kind = value.get("kind")
    if kind == "field":
        source = value.get("source")
        path = value.get("path")
        if isinstance(source, str):
            parts = path if isinstance(path, list) else []
            top = parts[0] if parts and isinstance(parts[0], str) else ""
            result["field"] = ["data", "field", f"{source}.{top}"]
            result["path"] = parts[1:]
    elif kind == "operation":
        operator = value.get("operator")
        if isinstance(operator, str):
            result["operator"] = ["expressions", "operation", operator]
        arguments = value.get("arguments")
        if isinstance(arguments, list):
            result["arguments"] = [expression(entry) for entry in arguments]
    return result


def expression_sources(value: Any) -> set[str]:
    sources: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for entry in node:
                visit(entry)
            return
        if not isinstance(node, dict):
            return
        if node.get("kind") == "field" and isinstance(node.get("source"), str):
            sources.add(node["source"])
        for key in ("arguments", "parameters"):
            visit(node.get(key))

    visit(value)
    return sources


def row_source(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    result = dict(value)
    source = value.get("source")
    if isinstance(source, str):
        result["kind"] = value.get("kind", "scan")
        result["relation"] = ["data", "relation", source]
        result.pop("source", None)
    if isinstance(value.get("left"), dict):
        result["left"] = row_source(value["left"])
    if isinstance(value.get("right"), dict):
        result["right"] = row_source(value["right"])
    if isinstance(value.get("inputs"), list):
        result["inputs"] = [row_source(entry) for entry in value["inputs"]]
    return result


def artifact_type(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    namespace = value.get("namespace")
    name = value.get("name")
    if not isinstance(namespace, str):
        return []
    parts = [namespace]
    if isinstance(name, str):
        parts.extend(part for part in name.split(".") if part)
    return parts


def field(value: Any, owner: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"name": "", "logical_type": {"kind": "unit", "name": "str"}}
    result: dict[str, Any] = {
        "name": str(value.get("name", "")),
        "logical_type": value.get("logical_type") or {"kind": "unit", "name": "str"},
        "ref": ["data", "field", f"{owner}.{value.get('name', '')}"],
        "annotations": annotations(value.get("annotations")),
    }
    definition = annotation_argument(value.get("annotations"), "definition")
    if definition:
        result["description"] = definition
    if value.get("expression") is not None:
        result["expression"] = expression(value["expression"])
    return result


def component_ref(kind: str, name: Any) -> list[str] | None:
    return ["topology", kind, name] if isinstance(name, str) and name else None


def property_entry(value: Any, component: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "name": "",
            "logical_type": {"kind": "unit", "name": "str"},
            "ref": ["topology", "property", component],
            "annotations": [],
        }
    name = str(value.get("name", ""))
    result: dict[str, Any] = {
        "name": name,
        "logical_type": value.get("logical_type") or {"kind": "unit", "name": "str"},
        "ref": ["topology", "property", f"{component}.{name}"],
        "annotations": annotations(value.get("annotations")),
    }
    definition = annotation_argument(value.get("annotations"), "definition")
    if definition:
        result["description"] = definition
    return result


def edge_label(value: dict[str, Any]) -> str | None:
    for entry in annotations(value.get("annotations")):
        if (
            entry.get("namespace") == "kg_build_system.topology"
            and entry.get("id") == "edge_label"
        ):
            label = (entry.get("arguments") or {}).get("label")
            if isinstance(label, str) and label:
                return label
    return None


def topology_component(value: dict[str, Any]) -> dict[str, Any]:
    kind = str(value.get("kind", ""))
    name = str(value.get("name", ""))
    result: dict[str, Any] = {
        "name": name,
        "labels": [edge_label(value) or name],
        "abstract": bool(value.get("abstract", False)),
        "properties": [property_entry(entry, name) for entry in value.get("properties") or []],
        "annotations": annotations(value.get("annotations")),
    }
    description = value.get("description") or annotation_argument(
        value.get("annotations"), "definition"
    )
    if description:
        result["description"] = description
    parent = value.get("parent")
    if isinstance(parent, str) and parent:
        result["parent"] = ["topology", kind, parent]
    if kind == "edge":
        result["source"] = component_ref("node", value.get("source"))
        result["target"] = component_ref("node", value.get("target"))
    return result


def projection_row_source(value: dict[str, Any]) -> dict[str, Any]:
    sources: set[str] = set()
    for entry in value.get("fields") or []:
        sources.update(expression_sources(entry.get("expression")))
    ordered = sorted(sources)
    if not ordered:
        return {"kind": "values", "filters": []}
    if len(ordered) == 1:
        return {
            "kind": "scan",
            "relation": ["data", "relation", ordered[0]],
            "filters": [],
        }
    return {
        "kind": "union",
        "inputs": [
            {"kind": "scan", "relation": ["data", "relation", source], "filters": []}
            for source in ordered
        ],
        "filters": [],
    }


def build_blueprint(source: dict[str, Any], tables: list[str]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    component_names = {
        value.get("symbol_id"): value.get("name")
        for value in source.get("components") or []
        if isinstance(value, dict)
        and isinstance(value.get("symbol_id"), str)
        and isinstance(value.get("name"), str)
    }
    for value in source.get("components") or []:
        if not isinstance(value, dict):
            continue
        kind = value.get("kind")
        if kind in ("node", "edge"):
            component = topology_component(value)
            parent = value.get("parent")
            if isinstance(parent, str) and parent:
                parent_name = component_names.get(parent) or parent.rsplit(":", 1)[-1]
                component["parent"] = ["topology", kind, parent_name]
            if kind == "node":
                nodes.append(component)
            else:
                edges.append(component)

    structs = []
    for value in source.get("structs") or []:
        if not isinstance(value, dict):
            continue
        structs.append(
            {
                "name": value.get("name", ""),
                "columns": [field(entry, value.get("name", "")) for entry in value.get("fields") or []],
                "annotations": annotations(value.get("annotations")),
                "description": annotation_argument(value.get("annotations"), "definition"),
            }
        )

    relations = []
    for value in source.get("tables") or []:
        if not isinstance(value, dict):
            continue
        relations.append(
            {
                "name": value.get("name", ""),
                "columns": [field(entry, value.get("name", "")) for entry in value.get("fields") or []],
                "annotations": annotations(value.get("annotations")),
                "description": annotation_argument(value.get("annotations"), "definition"),
                "asset": ["asset", "asset", ASSET_NAME],
            }
        )

    projections = []
    for value in source.get("projections") or []:
        if not isinstance(value, dict):
            continue
        projections.append(
            {
                "name": value.get("name", ""),
                "columns": [field(entry, value.get("name", "")) for entry in value.get("fields") or []],
                "annotations": annotations(value.get("annotations")),
                "description": value.get("description")
                or annotation_argument(value.get("annotations"), "definition"),
                "row_source": projection_row_source(value),
                "asset": ["asset", "asset", ASSET_NAME],
            }
        )

    bindings = []
    for value in source.get("bindings") or []:
        if not isinstance(value, dict):
            continue
        kind = value.get("kind")
        component = value.get("component")
        binding: dict[str, Any] = {
            "kind": kind,
            "properties": {
                name: expression(entry)
                for name, entry in (value.get("properties") or {}).items()
            },
            "annotations": annotations(value.get("annotations")),
            "mode": "source" if isinstance(value.get("row_source"), dict) else "derived",
            "symbol_id": value.get("symbol_id"),
            "debug_name": value.get("debug_name"),
        }
        if kind == "node":
            binding["node"] = component_ref("node", component)
        elif kind == "edge":
            binding["edge"] = component_ref("edge", component)
        if value.get("build_key") is not None:
            binding["identity"] = expression(value["build_key"])
        if value.get("source_build_key") is not None:
            binding["source_identity"] = expression(value["source_build_key"])
        if value.get("target_build_key") is not None:
            binding["target_identity"] = expression(value["target_build_key"])
        if value.get("row_source") is not None:
            binding["rows"] = row_source(value["row_source"])
        bindings.append(binding)

    asset = {
        "name": ASSET_NAME,
        "website": "https://platform.opentargets.org",
        "version": "26.09",
        "layout": {
            "kind": "parquet",
            "locator": ASSET_LOCATOR,
            "format": "parquet",
            "selector": "{table_path}/*.parquet",
            "partition_by": [],
            "members": {table: f"{table}/*.parquet" for table in tables},
            "properties": {},
        },
        "semantics": {
            "subject": "target-disease associations and supporting evidence",
            "coverage": "the Open Targets 26.09 platform output",
            "authority": "primary",
            "basis": "Open Targets Platform release 26.09",
            "claims": ["each table is one hive-partitioned parquet directory"],
            "limitations": [
                "nullability follows the parquet schema, not curation intent",
            ],
            "title": None,
            "description": None,
        },
        "governance": {"license": None, "owner": None, "metadata": {}},
        "annotations": [],
    }

    return {
        "graph": {"nodes": nodes, "edges": edges},
        "data": {
            "structs": structs,
            "relations": relations,
            "projections": projections,
        },
        "assets": [asset],
        "bindings": bindings,
    }


def instruction_for(
    module: str,
    step_name: str,
    instructions: dict[str, Any],
) -> dict[str, Any]:
    value = instructions.get(step_name)
    payload: dict[str, Any] = dict(value) if isinstance(value, dict) else {}
    if "sql" in payload and isinstance(payload["sql"], str):
        sql = payload["sql"]
        payload["sql"] = (
            sql
            if len(sql) <= SQL_PREVIEW_LIMIT
            else f"{sql[:SQL_PREVIEW_LIMIT]}\n-- truncated by the viewer snapshot builder"
        )
    if module == "core":
        action = payload.get("action") or "relation"
        kind = [str(action), MODULE_ENGINES["core"]]
    elif module == "collapse_exact_duplicates":
        kind = ["deduplication", MODULE_ENGINES[module]]
        payload = {
            "action": "deduplicate",
            **({"relation": payload["relation"]} if "relation" in payload else {}),
        }
    elif module == "file":
        kind = ["file", MODULE_ENGINES[module]]
        payload = {"action": "write"}
    elif module == "meta_graph":
        kind = ["meta_graph", MODULE_ENGINES[module]]
        components = payload.get("components")
        payload = {
            "action": "document",
            **({"components": len(components)} if isinstance(components, list) else {}),
        }
    elif module == "neo4j":
        kind = ["neo4j", MODULE_ENGINES[module]]
        component = payload.get("component")
        payload = {
            "action": payload.get("action", "export_component"),
            **(
                {"component": component.get("component")}
                if isinstance(component, dict) and component.get("component")
                else {}
            ),
        }
    elif module == "semantics":
        kind = ["semantics", MODULE_ENGINES[module]]
        payload = {"action": "semantics", "document": "semantics.json"}
    else:
        kind = [module or "module", "default"]
    return {"kind": kind, "payload": payload}


def build_workflow(contract: dict[str, Any]) -> dict[str, Any]:
    workflow = contract.get("workflow") or {}
    contributions = workflow.get("contributions") or []
    components: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    steps_by_module: dict[str, list[str]] = defaultdict(list)
    declared_openings: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    for contribution in contributions:
        if not isinstance(contribution, dict):
            continue
        reference = contribution.get("reference") or {}
        module = str(reference.get("module_id", ""))
        components.append(
            {
                "id": module,
                "version": str(reference.get("implementation_version", "")),
                "runtime_fields": contribution.get("runtime_fields") or [],
            }
        )
        for step in contribution.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("name"), str):
                steps_by_module[module].append(step["name"])

    for contribution in contributions:
        if not isinstance(contribution, dict):
            continue
        reference = contribution.get("reference") or {}
        module = str(reference.get("module_id", ""))
        variables = contribution.get("variables") or {}
        instructions = (
            variables.get("instructions")
            if isinstance(variables, dict)
            and isinstance(variables.get("instructions"), dict)
            else {}
        )
        for step in contribution.get("steps") or []:
            if not isinstance(step, dict):
                continue
            name = str(step.get("name", ""))
            inputs = []
            for entry in step.get("inputs") or []:
                if not isinstance(entry, dict):
                    continue
                local = entry.get("input_name") or entry.get("name") or "input"
                declared_openings[(module, name, "input")].append(str(local))
                inputs.append(
                    {
                        "declared_name": entry.get("name"),
                        "opening_name": [local],
                        "type": artifact_type(entry.get("type")),
                    }
                )
            outputs = []
            for entry in step.get("outputs") or []:
                if not isinstance(entry, dict):
                    continue
                local = entry.get("name") or "output"
                declared_openings[(module, name, "output")].append(str(local))
                outputs.append(
                    {
                        "kind": entry.get("kind") or "output",
                        "opening_name": [local],
                        "type": artifact_type(entry.get("type")),
                    }
                )
            steps.append(
                {
                    "id": [module, name],
                    "inputs": inputs,
                    "outputs": outputs,
                    "instruction": instruction_for(module, name, instructions),
                    "assembly_preference": "eager",
                }
            )

    def parse_id(value: Any, direction: str) -> list[str]:
        if not isinstance(value, str) or "::" not in value:
            raise ValueError(f"Unrecognised connection id: {value!r}")
        module, rest = value.split("::", 1)
        candidates = steps_by_module.get(module, [])
        matches = [
            step
            for step in candidates
            if rest == step or rest.startswith(f"{step}.")
        ]
        if not matches:
            raise ValueError(f"No step matches connection id: {value!r}")
        step = max(matches, key=len)
        opening = rest[len(step) + 1 :] if rest != step else ""
        if not opening:
            opening = "output" if direction == "output" else "input"

        # A local opening can itself contain dots or colons
        # (`binding.binding:edge:...`), while other openings carry an artifact
        # suffix (`records:core.graph.edge.foo`). Resolve against the step's
        # declared opening names so the first connection part is always the
        # exact local name.
        declared = sorted(
            declared_openings.get((module, step, direction), []),
            key=len,
            reverse=True,
        )
        local = next(
            (
                candidate
                for candidate in declared
                if opening == candidate or opening.startswith(f"{candidate}:")
            ),
            opening,
        )
        suffix = opening[len(local) + 1 :] if opening.startswith(f"{local}:") else ""
        parts = [local, *([suffix] if suffix else [])]
        return [module, step, direction, *parts]

    connections = []
    for value in workflow.get("connections") or []:
        if not isinstance(value, dict):
            continue
        connections.append(
            {
                "input": parse_id(value.get("input_id"), "input"),
                "output": parse_id(value.get("output_id"), "output"),
            }
        )

    return {
        "components": components,
        "steps": steps,
        "connections": connections,
        "provenance": {
            "source": "open_targets_kg/build/workflow_contract.json",
            "schema_version": contract.get("schema_version"),
            "workflow_fingerprint": contract.get("workflow_fingerprint"),
        },
    }


def build_report(report: dict[str, Any]) -> dict[str, Any]:
    published = []
    for value in report.get("published_artifacts") or []:
        if not isinstance(value, dict):
            continue
        type_parts = artifact_type(value.get("type"))
        opening = value.get("opening")
        if not isinstance(opening, list) or not opening:
            opening = ["report", "published", *type_parts]
        published.append(
            {
                "opening": opening,
                "type": type_parts,
                "value": value.get("value") or {},
            }
        )
    return {
        "published_artifacts": published,
        "recovered_failures": report.get("recovered_failures") or [],
        "unresolved_failures": report.get("unresolved_failures") or [],
        "provenance": {"source": "open_targets_kg/build/build_report.json"},
    }


def build_review(semantics: dict[str, Any]) -> dict[str, Any]:
    release = semantics.get("release")
    coverage = semantics.get("coverage") or {}
    components = coverage.get("components")
    properties = coverage.get("properties")
    bindings = coverage.get("bindings")
    description = semantics.get("description")
    rationale = " ".join(
        part
        for part in [
            f"Release {release}." if release else "",
            description or "",
            f"Coverage: {components} components, {bindings} bindings and {properties} properties."
            if components is not None
            else "",
        ]
        if part
    )
    return {
        "format": "kg-viewer-review",
        "version": 1,
        "ai": {
            "note": "No model, prompt, run identity or confidence was captured in the Open Targets build artifacts. Decisions below are derived from the workflow contract, blueprint and semantics catalogue."
        },
        "decisions": [
            {
                "id": "open-targets-release",
                "title": f"Open Targets Platform release {release}",
                "status": "accepted",
                "rationale": rationale,
                "subject": {"kind": "asset", "name": ASSET_NAME, "component": ASSET_NAME},
                "evidence": [
                    {
                        "label": "semantics catalogue release",
                        "artifact": "report",
                        "jsonPointer": "/provenance",
                    }
                ],
                "tags": ["release", "semantics"],
            },
            {
                "id": "one-parquet-asset",
                "title": "One logical parquet asset backs all tables",
                "status": "accepted",
                "rationale": "The project declares one OpenTargets asset with a hive-partitioned parquet layout. Each table is one directory under the release output, not a separate asset.",
                "subject": {"kind": "asset", "name": ASSET_NAME, "component": ASSET_NAME},
                "evidence": [
                    {
                        "label": "asset layout",
                        "artifact": "blueprint",
                        "jsonPointer": "/assets/0/layout",
                    }
                ],
                "tags": ["asset", "source-layout"],
            },
        ],
        "notes": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("~/Repos/opentargets-kg").expanduser(),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("viewer/public/data/opentargets.snapshot.json"),
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=Path("viewer/public/data/opentargets.review.json"),
    )
    parser.add_argument("--title", default="Open Targets 26.09 Knowledge Graph")
    args = parser.parse_args()

    build = args.project / "open_targets_kg" / "build"
    contract = read_json(build / "workflow_contract.json")
    blueprint_source = contract["provenance"]["compile"]["blueprint"]
    tables = [
        value.get("name")
        for value in blueprint_source.get("tables") or []
        if isinstance(value, dict) and value.get("name")
    ]
    blueprint = build_blueprint(blueprint_source, tables)
    workflow = build_workflow(contract)
    report = build_report(read_json(build / "build_report.json"))
    meta_graph = read_json(build / "meta_graph.json")
    semantics = read_json(build / "semantics.json")

    snapshot = {
        "format": "kg-viewer-snapshot",
        "version": 1,
        "name": "open-targets-26.09",
        "title": args.title,
        "blueprint": blueprint,
        "workflow": workflow,
        "report": report,
        "metaGraph": meta_graph,
    }
    review = build_review(semantics)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    args.review_output.write_text(
        json.dumps(review, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "snapshot": str(args.output),
                "bytes": args.output.stat().st_size,
                "review": str(args.review_output),
                "nodes": len(blueprint["graph"]["nodes"]),
                "edges": len(blueprint["graph"]["edges"]),
                "relations": len(blueprint["data"]["relations"]),
                "projections": len(blueprint["data"]["projections"]),
                "bindings": len(blueprint["bindings"]),
                "steps": len(workflow["steps"]),
                "connections": len(workflow["connections"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
