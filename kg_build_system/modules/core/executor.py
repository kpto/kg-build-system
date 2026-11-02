"""The core module's executor: decode one instruction and dispatch it."""
from __future__ import annotations

from typing import Any

from ...kernel import StepOutcome
from .._runtime import execution_services, instruction_payload, skipped
from .instructions import handle_instruction
from .ir import decode_core_instruction


class CoreExecutor:
    """Run one core step from the instruction the compiler filed for it."""

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


__all__ = ["CoreExecutor"]
