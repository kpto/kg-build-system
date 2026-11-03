"""The core module's executor: decode one instruction and dispatch it."""
from __future__ import annotations

from typing import Any

from ......kernel import StepOutcome
from ...service.instructions import nested_instruction
from ...service.runtime import (
    execution_services,
    instruction_payload,
    skipped,
)
from ...dto.instruction_codec import decode_core_instruction
from .instructions import handle_instruction


def execute_instruction(context: Any, instruction: Any) -> StepOutcome:
    """Run one core step from a stable Python instruction reference."""
    services = execution_services(context)
    core = decode_core_instruction(nested_instruction(instruction))
    return handle_instruction(context, core, services)


class CoreExecutor:
    """Run one core step from the compatibility instruction payload."""

    def handle(
        self, context: Any, services: Any = None,
    ) -> StepOutcome:
        services = execution_services(context, services)
        instruction = decode_core_instruction(instruction_payload(context))
        return handle_instruction(context, instruction, services)

    def handle_disrupted(
        self, context: Any, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


__all__ = ["CoreExecutor", "execute_instruction"]
