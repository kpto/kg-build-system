"""Assembly of the meta-graph document from its static and observed halves."""
from __future__ import annotations

from typing import Any

from .ir import MetaGraphDocumentIR
from .observation import (
    Observed, _inclusive_records, _inclusive_values,
)


def build_document(
    instruction: MetaGraphDocumentIR,
    observed: dict[tuple[str, str], Observed],
    location: str,
    *,
    module_id: str,
    module_version: str,
) -> dict[str, Any]:
    """Combine the compiled topology with what this step observed."""
    index = {
        (item.kind, item.name): item for item in instruction.components
    }
    examples_enabled = instruction.example_limit > 0
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    totals = {"node": 0, "edge": 0}
    for component in sorted(
        instruction.components, key=lambda item: (item.kind, item.symbol_id),
    ):
        entry = component.model_dump(mode="json")
        records = 0 if component.abstract else observed.get(
            (component.kind, component.name), Observed(),
        ).records
        if not component.abstract:
            totals[component.kind] += records
        entry["counts"] = {
            "records": records,
            "inclusive_records": _inclusive_records(component, index, observed),
            "bindings": len(component.bindings),
            "declared_children": len(component.children),
        }
        if examples_enabled:
            values = _inclusive_values(
                component, index, observed, instruction.example_limit,
            )
            for prop in entry["properties"]:
                prop["examples"] = values.get(prop["name"], [])
        (nodes if component.kind == "node" else edges).append(entry)
    return {
        "generated_by": {
            "module_id": module_id,
            "module_version": module_version,
        },
        "examples": {
            "method": "approx_top_k",
            "limit": instruction.example_limit,
        },
        "summary": {
            "node_components": len(nodes),
            "edge_components": len(edges),
            "abstract_components": sum(
                1 for item in instruction.components if item.abstract
            ),
            "total_nodes": totals["node"],
            "total_edges": totals["edge"],
            "location": location,
        },
        "nodes": nodes,
        "edges": edges,
    }


__all__ = ["build_document"]
