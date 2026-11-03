"""Instruction dispatch: one executor per instruction kind."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from ....kernel import DisruptedExecutionContext, ExecutionContext, StepOutcome
from kg_build_system.kernel.internal.json import thaw_json

from .contract import Instruction


class UnknownInstructionKind(LookupError):
    """A step named an instruction kind this build does not implement."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(f"unknown instruction kind {kind!r}")


class InstructionExecutor(Protocol):
    """Execute one instruction against a step's execution context."""

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Run the instruction and return the step outcome."""
        ...


def instruction_payload(instruction: Instruction) -> Mapping[str, Any]:
    """Return one instruction payload as a plain JSON object.

    A payload that travelled through a contract is immutable and thawed here;
    one supplied directly by a compiler is already plain data. Both name the
    same object, and neither is read from another contract field.
    """
    value = thaw_json(instruction.payload)
    if not isinstance(value, Mapping):
        raise TypeError(
            f"instruction kind {instruction.kind!r} requires an object payload"
        )
    return value


class InstructionDispatcher:
    """Select an executor by ``instruction.kind`` and run it.

    A kind with a registered executor takes priority. A kind without one is
    offered to the fallback, which resolves the step's contribution module. A
    dispatcher with no fallback, or a fallback that finds no module executor,
    refuses the kind with :class:`UnknownInstructionKind`.
    """

    def __init__(
        self,
        executors: Mapping[str, InstructionExecutor],
        *,
        fallback: InstructionExecutor | None = None,
    ) -> None:
        self._executors = dict(executors)
        self._fallback = fallback

    @property
    def kinds(self) -> tuple[str, ...]:
        """The instruction kinds this dispatcher names explicitly."""
        return tuple(sorted(self._executors))

    def register(self, kind: str, executor: InstructionExecutor) -> None:
        """Add or replace the executor for one kind."""
        if not isinstance(kind, str) or not kind:
            raise ValueError("an instruction kind must be a non-empty string")
        self._executors[kind] = executor

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Dispatch one instruction, refusing a kind no executor handles."""
        executor = self._executors.get(instruction.kind)
        if executor is not None:
            return executor.execute(context, instruction)
        if self._fallback is not None:
            return self._fallback.execute(context, instruction)
        raise UnknownInstructionKind(instruction.kind)


__all__ = [
    "InstructionDispatcher",
    "InstructionExecutor",
    "UnknownInstructionKind",
    "instruction_payload",
]
