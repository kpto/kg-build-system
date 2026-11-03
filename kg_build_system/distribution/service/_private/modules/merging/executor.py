"""Execution of the compatible-facts merging step."""
from __future__ import annotations

from typing import Any

from ......kernel import (
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
_MERGED_OUTPUT = "merged"


def execute_instruction(context: Any, instruction: Any) -> StepOutcome:
    """Run one merge step from a stable Python instruction reference."""
    local = nested_instruction(instruction)
    if local.kind != "merging":
        raise ValueError(f"unexpected merging instruction {local.kind!r}")
    return _run(context, as_mapping(local.payload, context="merging payload"))


class MergingExecutor:
    """Run one merge step from its compatibility instruction payload."""

    def handle(
        self, context: ExecutionContext, services: Any = None,
    ) -> StepOutcome:
        instruction = decode_instruction(instruction_payload(context))
        if instruction.kind != "merging":
            raise ValueError(f"unexpected merging instruction {instruction.kind!r}")
        return _run(context, as_mapping(
            instruction.payload, context="merging payload",
        ))

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


def _run(context: Any, payload: Any) -> StepOutcome:
    services = execution_services(context)
    input_relation = next(
        (
            item.artifact.value
            for item in context.inputs[_RECORDS_INPUT]
            if item.artifact is not None
        ),
        None,
    )
    if input_relation is None:
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
        )

    source = services.relations.reference(input_relation)
    relation = services.relations.materialize(
        str(payload["relation"]),
        f'SELECT {payload["select"]} FROM {source} GROUP BY "build_key"',
    )
    outputs = {output_name(given): given for given in context.step.outputs}
    artifact = Artifact(
        _MERGED_OUTPUT, outputs[_MERGED_OUTPUT].type, relation,
    )
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=StepStatus.SUCCEEDED,
        artifacts=(artifact,),
    )


__all__ = ["MergingExecutor", "execute_instruction"]
