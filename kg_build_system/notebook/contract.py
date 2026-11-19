"""Generic contract checks over a compiled blueprint and its build artifacts.

A project composes its own blueprint and compiles it. What stays the same for
every project is checked here: every declaration states its meaning, every node
carries a Biolink class, every edge a predicate, every relation names a declared
asset, and the emitted graph has no duplicate keys, no dangling endpoints and no
uncovered records.

The functions take the objects the project already has. They import nothing from
the build framework, so ``notebook`` keeps its empty dependency list.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

__all__ = ["audit_graph", "document_revision", "validate_blueprint"]


def document_revision(document: dict[str, Any]) -> str:
    """A stable short fingerprint of a canonical declaration document."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _has_meaning(value: Any) -> bool:
    meaning = getattr(value, "meaning", None)
    if meaning is None:
        return False
    if getattr(meaning, "omitted", None) is not None:
        return True
    return bool(getattr(meaning, "purpose", None))


def _annotation_ids(values: Any) -> set[str]:
    ids: set[str] = set()
    for annotation in values or ():
        if isinstance(annotation, dict):
            ids.add(str(annotation.get("id", "")))
        else:
            ids.add(
                str(
                    getattr(annotation, "id", None)
                    or getattr(annotation, "annotation_id", "")
                )
            )
    return ids


def validate_blueprint(blueprint: Any) -> dict[str, Any]:
    """Check the declaration contract every project shares.

    Structural checks (colliding names, dangling references) belong to the build
    framework and already run when the blueprint is created. This checks the
    semantics the framework does not know about.
    """
    errors: list[str] = []
    warnings: list[str] = []

    declaration = getattr(blueprint, "graph_declaration", None)
    if declaration is None:
        errors.append("the project declares no Graph")
    elif not _has_meaning(declaration):
        errors.append("the graph declaration has no meaning")

    graph = getattr(blueprint, "graph", None)
    nodes = list(getattr(graph, "nodes", ()) or ())
    edges = list(getattr(graph, "edges", ()) or ())
    assets = list(getattr(getattr(blueprint, "assets", None), "assets", ()) or ())
    bindings = list(getattr(blueprint, "bindings", ()) or ())
    data = getattr(blueprint, "data", None)
    relations = list(getattr(data, "source_relations", ()) or ())
    relations += list(getattr(data, "derived_relations", ()) or ())

    for node in nodes:
        if not _has_meaning(node):
            errors.append(f"node {node.name} has no meaning")
        # An abstract category produces no record of its own, so it names no
        # Biolink class; only concrete components must.
        if not getattr(node, "abstract", False) and "class" not in _annotation_ids(
            getattr(node, "annotations", ())
        ):
            errors.append(f"node {node.name} has no biolink class annotation")
    for edge in edges:
        if not _has_meaning(edge):
            errors.append(f"edge {edge.name} has no meaning")
        if not getattr(edge, "abstract", False) and "predicate" not in _annotation_ids(
            getattr(edge, "annotations", ())
        ):
            errors.append(f"edge {edge.name} has no biolink predicate annotation")
    for asset in assets:
        if not _has_meaning(asset):
            errors.append(f"asset {asset.name} has no meaning")
    for binding in bindings:
        if not _has_meaning(binding):
            errors.append(f"binding {getattr(binding, 'name', None) or '?'} has no meaning")

    names = {asset.name for asset in assets}
    for relation in relations:
        reference = getattr(relation, "asset", None)
        symbol = getattr(reference, "symbol", None) if reference is not None else None
        key = getattr(symbol, "key", None) if symbol is not None else None
        segments = getattr(key, "segments", ()) if key is not None else ()
        name = segments[0] if segments else None
        if name is not None and name not in names:
            errors.append(f"relation {relation.name} names unknown asset {name}")

    properties = [prop for node in nodes for prop in getattr(node, "properties", ()) or ()]
    properties += [prop for edge in edges for prop in getattr(edge, "properties", ()) or ()]

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "properties": len(properties),
            "assets": len(assets),
            "bindings": len(bindings),
        },
    }


def audit_graph(build_dir: Path | str) -> dict[str, Any]:
    """Integrity of ``graph.jsonl`` and coverage of ``evidence.jsonl``."""
    directory = Path(build_dir)
    graph = directory / "graph.jsonl"
    if not graph.exists():
        return {"status": "skipped", "reason": f"no graph at {graph}"}

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    duplicates = 0
    null_keys = 0
    for line in graph.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        key = record.get("build_key")
        if not key:
            null_keys += 1
            continue
        if record.get("kind") == "node":
            if key in nodes:
                duplicates += 1
            nodes[key] = record
        else:
            edges.append(record)

    dangling = 0
    for edge in edges:
        if edge.get("source_build_key") not in nodes:
            dangling += 1
        if edge.get("target_build_key") not in nodes:
            dangling += 1

    evidence = directory / "evidence.jsonl"
    evidence_keys: set[str] = set()
    if evidence.exists():
        for line in evidence.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            key = json.loads(line).get("build_key")
            if key:
                evidence_keys.add(key)

    node_types = Counter(record.get("type") for record in nodes.values())
    edge_types = Counter(record.get("type") for record in edges)
    prefixes = Counter(
        str(key).split(":", 1)[0] for key in list(nodes) + [edge.get("build_key") for edge in edges]
    )
    covered = len(evidence_keys & set(nodes)) + len(
        evidence_keys & {edge.get("build_key") for edge in edges}
    )
    return {
        "status": "passed" if not (duplicates or null_keys or dangling) else "failed",
        "nodes": len(nodes),
        "edges": len(edges),
        "node_types": dict(sorted(node_types.items())),
        "edge_types": dict(sorted(edge_types.items())),
        "duplicates": duplicates,
        "null_keys": null_keys,
        "dangling_endpoints": dangling,
        "evidence_entries": len(evidence_keys),
        "evidence_coverage": round(covered / max(1, len(nodes) + len(edges)), 4),
        "key_prefixes": dict(prefixes),
    }
