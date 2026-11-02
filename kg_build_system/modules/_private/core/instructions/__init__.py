"""Instruction handlers, keyed by the instruction's own action.

A new core instruction is one handler module plus one registry entry. The
executor never tests instruction classes and never grows a fallback chain.
"""
from __future__ import annotations

from typing import Any, Callable

from .....kernel import StepOutcome
from ..ir import CoreStepInstructionIR
from .aggregate import handle_aggregate
from .relation import handle_relation
from .source_relation import handle_source_relation


InstructionHandler = Callable[[Any, Any, Any], StepOutcome]

INSTRUCTION_HANDLERS: dict[str, InstructionHandler] = {
    "source_relation": handle_source_relation,
    "relation": handle_relation,
    "aggregate": handle_aggregate,
}

#: Compatibility spelling for callers that name the registry by its role.
HANDLERS = INSTRUCTION_HANDLERS


def handle_instruction(
    context: Any,
    instruction: CoreStepInstructionIR,
    services: Any,
) -> StepOutcome:
    try:
        handler = INSTRUCTION_HANDLERS[instruction.action]
    except KeyError as error:
        raise ValueError(
            f"unknown core instruction action {instruction.action!r}"
        ) from error
    return handler(context, instruction, services)


__all__ = [
    "HANDLERS",
    "INSTRUCTION_HANDLERS",
    "InstructionHandler",
    "handle_instruction",
]
