"""Deterministic assembly of ordered workflow-module contributions."""
from __future__ import annotations

from collections.abc import Sequence

from .models import (
    Connection, OutputSlot, SingleInputSlot, WorkflowContribution,
    WorkflowDefinition,
)
from .validation import validate_workflow


def assemble_workflow(
    contributions: Sequence[WorkflowContribution],
) -> WorkflowDefinition:
    drafts = [draft for contribution in contributions for draft in contribution.steps]
    modules = tuple(contribution.module for contribution in contributions)
    if len({module.reference.module_id for module in modules}) != len(modules):
        raise ValueError("workflow module IDs must be unique")

    module_order = {
        module.reference.module_id: index for index, module in enumerate(modules)
    }
    declaration_order = {
        draft.definition.step_id: index for index, draft in enumerate(drafts)
    }
    output_step = {
        slot.slot_id: draft.definition.step_id
        for draft in drafts for slot in draft.definition.outputs
    }
    outputs = [slot for draft in drafts for slot in draft.definition.outputs]
    output_order = {slot.slot_id: index for index, slot in enumerate(outputs)}
    output_module = {
        slot.slot_id: draft.definition.module_id
        for draft in drafts for slot in draft.definition.outputs
    }
    dependencies: dict[str, set[str]] = {
        draft.definition.step_id: set() for draft in drafts
    }

    def creates_cycle(producer: str, consumer: str) -> bool:
        if producer == consumer:
            return True
        pending = [consumer]
        visited: set[str] = set()
        while pending:
            step_id = pending.pop()
            if step_id == producer:
                return True
            if step_id in visited:
                continue
            visited.add(step_id)
            pending.extend(dependencies[step_id])
        return False

    def candidate_order(output: OutputSlot) -> tuple[int, int, str]:
        return (
            module_order[output_module[output.slot_id]],
            output_order[output.slot_id],
            output.slot_id,
        )

    claims = sorted(
        drafts,
        key=lambda draft: (
            0 if draft.assembly_preference == "eager" else 1,
            module_order[draft.definition.module_id]
            if draft.assembly_preference == "eager"
            else -module_order[draft.definition.module_id],
            declaration_order[draft.definition.step_id],
        ),
    )
    connections: list[Connection] = []
    uses: dict[str, int] = {}
    for draft in claims:
        for input_slot in draft.definition.inputs:
            predicate = draft.candidates.get(input_slot.slot_id)
            candidates = [
                output for output in outputs
                if output_step[output.slot_id] != draft.definition.step_id
                and predicate is not None
                and predicate(input_slot, output)
                and not creates_cycle(
                    output_step[output.slot_id], draft.definition.step_id,
                )
            ]
            if isinstance(input_slot, SingleInputSlot):
                if not candidates:
                    raise ValueError(
                        f"input {input_slot.slot_id} has no compatible output"
                    )
                open_candidates = [
                    output for output in candidates if uses.get(output.slot_id, 0) == 0
                ]
                selected = max(open_candidates or candidates, key=candidate_order)
                connections.append(Connection(input_slot.slot_id, selected.slot_id))
                uses[selected.slot_id] = uses.get(selected.slot_id, 0) + 1
                dependencies[output_step[selected.slot_id]].add(
                    draft.definition.step_id
                )
                continue

            by_role: dict[tuple[str, str], list[OutputSlot]] = {}
            for output in candidates:
                role = output.artifact_role
                by_role.setdefault((role.namespace, role.name), []).append(output)
            selected_outputs: list[OutputSlot] = []
            for role_candidates in by_role.values():
                open_candidates = [
                    output for output in role_candidates
                    if uses.get(output.slot_id, 0) == 0
                ]
                selected_outputs.extend(
                    open_candidates or (max(role_candidates, key=candidate_order),)
                )
            if not selected_outputs:
                raise ValueError(
                    f"input {input_slot.slot_id} has no compatible output"
                )
            for output in sorted(selected_outputs, key=candidate_order):
                connections.append(Connection(input_slot.slot_id, output.slot_id))
                uses[output.slot_id] = uses.get(output.slot_id, 0) + 1
                dependencies[output_step[output.slot_id]].add(
                    draft.definition.step_id
                )

    workflow = WorkflowDefinition(
        modules=modules,
        steps=tuple(draft.definition for draft in drafts),
        connections=tuple(connections),
    )
    validate_workflow(workflow)
    return workflow


__all__ = ["assemble_workflow"]
