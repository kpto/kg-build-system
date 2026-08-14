"""Validation services for workflow domain models."""
from __future__ import annotations

from .models import SingleInputSlot, WorkflowDefinition


def validate_workflow(value: WorkflowDefinition) -> None:
    module_ids = tuple(module.reference.module_id for module in value.modules)
    if len(module_ids) != len(set(module_ids)):
        raise ValueError("workflow module IDs must be unique")

    step_ids = tuple(step.step_id for step in value.steps)
    if len(step_ids) != len(set(step_ids)):
        raise ValueError("workflow step IDs must be unique")
    if any(step.module_id not in module_ids for step in value.steps):
        raise ValueError("workflow step references an unknown module")

    inputs = {slot.slot_id: slot for step in value.steps for slot in step.inputs}
    outputs = {slot.slot_id for step in value.steps for slot in step.outputs}
    if len(inputs) != sum(len(step.inputs) for step in value.steps):
        raise ValueError("workflow input slot IDs must be unique")
    if len(outputs) != sum(len(step.outputs) for step in value.steps):
        raise ValueError("workflow output slot IDs must be unique")

    counts: dict[str, int] = {}
    pairs: set[tuple[str, str]] = set()
    for connection in value.connections:
        if connection.input_slot_id not in inputs:
            raise ValueError("workflow connection references an unknown input slot")
        if connection.output_slot_id not in outputs:
            raise ValueError("workflow connection references an unknown output slot")
        pair = (connection.input_slot_id, connection.output_slot_id)
        if pair in pairs:
            raise ValueError("workflow connections must be unique")
        pairs.add(pair)
        counts[connection.input_slot_id] = counts.get(connection.input_slot_id, 0) + 1

    for slot_id, slot in inputs.items():
        count = counts.get(slot_id, 0)
        if count == 0:
            raise ValueError(f"input {slot_id!r} requires at least one connection")
        if isinstance(slot, SingleInputSlot) and count != 1:
            raise ValueError(f"single input {slot_id!r} requires exactly one connection")

    output_owners = {slot.slot_id: step.step_id for step in value.steps for slot in step.outputs}
    input_owners = {slot.slot_id: step.step_id for step in value.steps for slot in step.inputs}
    dependents: dict[str, set[str]] = {step.step_id: set() for step in value.steps}
    indegrees = {step.step_id: 0 for step in value.steps}
    for connection in value.connections:
        producer = output_owners[connection.output_slot_id]
        consumer = input_owners[connection.input_slot_id]
        if consumer not in dependents[producer]:
            dependents[producer].add(consumer)
            indegrees[consumer] += 1
    ready = [step_id for step_id, degree in indegrees.items() if degree == 0]
    visited = 0
    while ready:
        producer = ready.pop()
        visited += 1
        for consumer in dependents[producer]:
            indegrees[consumer] -= 1
            if indegrees[consumer] == 0:
                ready.append(consumer)
    if visited != len(value.steps):
        raise ValueError("workflow dependency graph contains a cycle")


__all__ = ["validate_workflow"]
