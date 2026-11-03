"""Execution of the exact-duplicate removal step."""
from __future__ import annotations

from typing import Any

from .....kernel import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    StepOutcome,
    StepStatus,
)
from ...dto.instruction_codec import decode_instruction
from ...service.instructions import nested_instruction
from ...service.runtime import (
    as_mapping,
    execution_services,
    instruction_payload,
    output_name,
    skipped,
)

_RECORDS_INPUT = "records"
_DISTINCT_OUTPUT = "distinct"


def execute_instruction(context: Any, instruction: Any) -> StepOutcome:
    """Run one distinct step from a stable Python instruction reference."""
    local = nested_instruction(instruction)
    if local.kind != "deduplication":
        raise ValueError(f"unexpected deduplication instruction {local.kind!r}")
    payload = as_mapping(local.payload, context="deduplication payload")
    return _run(context, payload)


class DeduplicationExecutor:
    """Run one distinct step from its compatibility instruction payload."""

    def handle(
        self, context: ExecutionContext, services: Any = None,
    ) -> StepOutcome:
        instruction = decode_instruction(instruction_payload(context))
        if instruction.kind != "deduplication":
            raise ValueError(
                f"unexpected deduplication instruction {instruction.kind!r}"
            )
        return _run(context, as_mapping(
            instruction.payload, context="deduplication payload",
        ))

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


def _run(context: Any, payload: Any) -> StepOutcome:
    services = execution_services(context)
    input_relation = next(
        item.artifact.value
        for item in context.inputs[_RECORDS_INPUT]
        if item.artifact is not None
    )
    source = services.relations.reference(input_relation)
    relation = services.relations.materialize(
        str(payload["relation"]), f"SELECT DISTINCT * FROM {source}",
    )
    outputs = {output_name(given): given for given in context.step.outputs}
    artifact = Artifact(
        _DISTINCT_OUTPUT, outputs[_DISTINCT_OUTPUT].type, relation,
    )
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=StepStatus.SUCCEEDED,
        artifacts=(artifact,),
    )


__all__ = ["DeduplicationExecutor", "execute_instruction"]
