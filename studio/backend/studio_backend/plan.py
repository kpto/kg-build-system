"""Project a compiled ``WorkflowContractIR`` into the plan the UI draws.

The contract already contains the whole execution DAG — steps, per-step input and
output slots with semantic artifact roles, and resolved connections between them.
What the compositor view additionally needs is presentation data the contract
deliberately does not carry: a human label per node, the IR reference a step belongs
to (so a build failure can light up the right component), a layer for layout, and
the payload fields worth showing inline.

Step identity is derived from the framework's step-id grammar
(``core::table.<name>``, ``core::binding.<n>``, ``core::aggregate.<component>``,
``<module>::export.node.<component>-<hash>``, ``file::write``, ``meta_graph::document``)
and from artifact role names, both of which are stable parts of the contract.
"""

from __future__ import annotations

import re
from typing import Any

from kg_build_system.workflow.ir import WorkflowContractIR, WorkflowStepIR

#: ``binding:edge:has_defect:4a77…`` — role and symbol ids both carry the component.
#: Unanchored because a role prefixes the symbol id with its namespace.
_SYMBOL_PATTERN = re.compile(r"binding:(?P<kind>node|edge):(?P<component>[a-z0-9_]+):")


def project_plan(contract: WorkflowContractIR) -> dict[str, Any]:
    definition = contract.workflow
    outputs = {
        output.slot_id: (step.step_id, output)
        for step in definition.steps
        for output in step.outputs
    }
    producers = {
        step.step_id: index for index, step in enumerate(definition.steps)
    }

    nodes = [_node(step, producers) for step in definition.steps]
    edges: list[dict[str, str]] = []
    for connection in definition.connections:
        producer = outputs.get(connection.output_slot_id)
        if producer is None:
            continue
        consumer_step = _slot_owner(definition.steps, connection.input_slot_id)
        if consumer_step is None:
            continue
        edges.append(
            {
                "id": f"{connection.output_slot_id}->{connection.input_slot_id}",
                "from_step": producer[0],
                "from_slot": connection.output_slot_id,
                "to_step": consumer_step,
                "to_slot": connection.input_slot_id,
                "role": _role_name(producer[1]),
            }
        )

    return {
        "fingerprint": contract.workflow_fingerprint,
        "modules": [
            {
                "id": module.reference.module_id,
                "label": _label(module.reference.module_id),
                "implementation_version": module.reference.implementation_version,
                "role": _module_role(module.reference.module_id),
                "runtime_fields": [field.key for field in module.runtime_fields],
            }
            for module in definition.modules
        ],
        "nodes": nodes,
        "edges": edges,
    }


def _node(step: WorkflowStepIR, producers: dict[str, int]) -> dict[str, Any]:
    payload = step.payload if isinstance(step.payload, dict) else {}
    kind, label, component = _classify(step, payload)
    return {
        "id": step.step_id,
        "module_id": step.module_id,
        "label": label,
        "kind": kind,
        "component": component,
        "order": producers[step.step_id],
        "inputs": [
            {"slot_id": slot.slot_id, "role": _role_for_input(step, slot.slot_id)}
            for slot in step.inputs
        ],
        "outputs": [
            {"slot_id": slot.slot_id, "role": _role_name(slot)} for slot in step.outputs
        ],
        "sql": payload.get("sql") if isinstance(payload.get("sql"), str) else None,
        "columns": _columns(payload),
        "format": payload.get("format") if isinstance(payload.get("format"), str) else None,
        "location": payload.get("location") if isinstance(payload.get("location"), str) else None,
        "target_path": _target_path(payload),
        "relation": payload.get("relation") if isinstance(payload.get("relation"), str) else None,
        "action": payload.get("action") if isinstance(payload.get("action"), str) else None,
        "notes": _notes(payload),
        "payload_keys": sorted(payload),
    }


def _classify(step: WorkflowStepIR, payload: dict[str, Any]) -> tuple[str, str, str | None]:
    """``(kind, label, ir_component)`` for one step."""
    step_id = step.step_id
    _, _, local = step_id.partition("::")
    role = next((_role_name(output) for output in step.outputs), "")

    if local.startswith("source."):
        name = local.removeprefix("source.")
        return "source", name, f"source:{name}" if _looks_like_name(name) else None
    if local.startswith("table."):
        name = local.removeprefix("table.")
        return "table", name, f"table:{name}" if _looks_like_name(name) else None
    if local.startswith("projection."):
        name = local.removeprefix("projection.")
        return "projection", name, f"projection:{name}" if _looks_like_name(name) else None
    if local.startswith("binding."):
        component = _component_from_role(role)
        kind = "binding"
        return kind, f"bind {component}" if component else local, (
            f"component:{component}" if component else None
        )
    if local.startswith("aggregate."):
        name = local.removeprefix("aggregate.")
        return "aggregate", name, f"component:{name}" if _looks_like_name(name) else None
    if step.module_id == "file" and local == "write":
        return "publish", "graph.jsonl", None
    if step.module_id == "meta_graph":
        return "document", "meta graph", None
    if local.startswith("export."):
        remainder = local.removeprefix("export.")
        side, _, name = remainder.partition(".")
        name = _strip_hash(name)
        return "export", f"{side}:{name}", f"component:{name}" if _looks_like_name(name) else None
    if local == "script":
        return "script", "import script", None
    if step.module_id in {"collapse_exact_duplicates", "merge_compatible_facts", "reject_conflicting_non_null_values"}:
        component = _component_from_role(role) or local
        return "operator", component, f"component:{component}" if _looks_like_name(component) else None
    return "step", local or step_id, None


def _component_from_role(role: str) -> str | None:
    # Binding output roles are ``core.binding.<binding symbol id>``, so the symbol
    # pattern is preceded by the role namespace and must be searched, not anchored.
    match = _SYMBOL_PATTERN.search(role)
    if match is not None:
        return match.group("component")
    # ``core:graph.node.site`` and ``core:graph.edge.has_unit`` carry the component.
    for prefix in ("graph.node.", "graph.edge."):
        marker = f"core:{prefix}"
        if role.startswith(marker):
            return role[len(marker) :]
    return None


def _looks_like_name(value: str) -> bool:
    return bool(value) and re.fullmatch(r"[a-z][a-z0-9_]*", value) is not None


def _strip_hash(value: str) -> str:
    return value.rsplit("-", 1)[0] if "-" in value else value


def _label(module_id: str) -> str:
    return " ".join(part.title() for part in module_id.split("_")) or module_id


def _module_role(module_id: str) -> str:
    if module_id == "core":
        return "core"
    if module_id in {"collapse_exact_duplicates", "merge_compatible_facts", "reject_conflicting_non_null_values"}:
        return "operator"
    return "target"


def _role_name(output: Any) -> str:
    role = getattr(output, "artifact_role", None)
    if role is None:
        return ""
    return f"{role.namespace}.{role.name}"


def _slot_owner(steps: tuple[WorkflowStepIR, ...], slot_id: str) -> str | None:
    for step in steps:
        for slot in step.inputs:
            if slot.slot_id == slot_id:
                return step.step_id
    return None


def _role_for_input(step: WorkflowStepIR, slot_id: str) -> str:
    """The input slot's own identity; its role is whatever feeds it.

    Inputs do not declare roles in the contract — only outputs do — so the UI
    labels an input socket with the slot name and colours the edge by the
    producer's role.
    """
    return slot_id.rpartition(".")[2]


def _columns(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Declared columns of a source step, name plus canonical type, for the node body."""
    columns = payload.get("declared_columns")
    if not isinstance(columns, list):
        return None
    projected: list[dict[str, Any]] = []
    for column in columns:
        if isinstance(column, dict) and isinstance(column.get("name"), str):
            logical = column.get("logical_type")
            projected.append({"name": column["name"], "logical_type": logical if isinstance(logical, dict) else None})
    return projected


def _target_path(payload: dict[str, Any]) -> str | None:
    """Where an export or document step writes, however that module words it."""
    for key in ("relative_path", "html_relative_path", "script_name", "relative_directory"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    for value in payload.values():
        if isinstance(value, dict):
            nested = _target_path(value)
            if nested is not None:
                return nested
    return None


def _notes(payload: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if payload.get("materialize"):
        notes.append("materialized")
    if isinstance(payload.get("relative_path"), str):
        notes.append(f"→ {payload['relative_path']}")
    if isinstance(payload.get("location"), str):
        notes.append(f"← {payload['location']}")
    if isinstance(payload.get("components"), list):
        notes.append(f"{len(payload['components'])} components")
    elif isinstance(payload.get("component"), str):
        notes.append(payload["component"])
    return notes
