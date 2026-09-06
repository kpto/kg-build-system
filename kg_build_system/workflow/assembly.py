"""Deterministic assembly of ordered workflow-module contributions."""
from __future__ import annotations

from collections.abc import Sequence

from .models import (
    Connection, OutputSlot, SingleInputSlot, WorkflowContribution,
    WorkflowDefinition,
)
from .validation import validate_workflow

type RoleKey = tuple[str, str]


def _role_key(output: OutputSlot) -> RoleKey:
    return (output.artifact_role.namespace, output.artifact_role.name)


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
    claim_rank = {
        draft.definition.step_id: index for index, draft in enumerate(claims)
    }

    # A relaying step both accepts a role and re-publishes it, so it extends
    # that role's pipeline chain (graph-record operators do exactly this).
    # Every consumer of a chained role must then read the chain's terminal
    # link among the steps that claimed before it — the artifact carrying
    # every earlier operator's effect — instead of whichever producer happens
    # to be unread, or raw pre-operator records would be exported as final.
    publishes: dict[str, set[RoleKey]] = {
        draft.definition.step_id: {_role_key(o) for o in draft.definition.outputs}
        for draft in drafts
    }
    can_consume: dict[str, set[RoleKey]] = {}
    for draft in drafts:
        consumed: set[RoleKey] = set()
        for input_slot in draft.definition.inputs:
            predicate = draft.candidates.get(input_slot.slot_id)
            if predicate is None:
                continue
            for output in outputs:
                if output_step[output.slot_id] == draft.definition.step_id:
                    continue
                if predicate(input_slot, output):
                    consumed.add(_role_key(output))
        can_consume[draft.definition.step_id] = consumed
    relay_roles: dict[str, set[RoleKey]] = {
        draft.definition.step_id: (
            publishes[draft.definition.step_id]
            & can_consume[draft.definition.step_id]
        )
        for draft in drafts
    }

    def candidate_order(output: OutputSlot) -> tuple[int, int, str]:
        return (
            module_order[output_module[output.slot_id]],
            output_order[output.slot_id],
            output.slot_id,
        )

    def chain_pick(
        role_key: RoleKey, group: list[OutputSlot], consumer_step: str,
    ) -> OutputSlot | None:
        """The artifact this consumer should read for a chained role."""
        relays = [
            output for output in group
            if role_key in relay_roles[output_step[output.slot_id]]
        ]
        if not relays:
            return None
        rank = claim_rank[consumer_step]
        upstream = [
            output for output in relays
            if claim_rank[output_step[output.slot_id]] < rank
        ]
        if upstream:
            return max(upstream, key=lambda o: claim_rank[output_step[o.slot_id]])
        raws = [output for output in group if output not in relays]
        if raws:
            return max(raws, key=candidate_order)
        return max(group, key=candidate_order)

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
                role_keys = {_role_key(output) for output in candidates}
                selected = None
                if len(role_keys) == 1:
                    selected = chain_pick(
                        next(iter(role_keys)), candidates, draft.definition.step_id,
                    )
                if selected is None:
                    open_candidates = [
                        output for output in candidates
                        if uses.get(output.slot_id, 0) == 0
                    ]
                    selected = max(open_candidates or candidates, key=candidate_order)
                connections.append(Connection(input_slot.slot_id, selected.slot_id))
                uses[selected.slot_id] = uses.get(selected.slot_id, 0) + 1
                dependencies[output_step[selected.slot_id]].add(
                    draft.definition.step_id
                )
                continue

            by_role: dict[RoleKey, list[OutputSlot]] = {}
            for output in candidates:
                by_role.setdefault(_role_key(output), []).append(output)
            selected_outputs: list[OutputSlot] = []
            for role_key, role_candidates in by_role.items():
                head = chain_pick(
                    role_key, role_candidates, draft.definition.step_id,
                )
                if head is not None:
                    selected_outputs.append(head)
                    continue
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
