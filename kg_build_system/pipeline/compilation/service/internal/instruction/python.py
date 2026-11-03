"""Python instruction emitter wrapper.

The emission mechanism lives in ``service._private``; this wrapper keeps the
internal instruction path stable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .....contract.model.public import InstructionDTO
from ....model.internal.instruction import PYTHON_INSTRUCTION_KIND, PythonReference


@dataclass(frozen=True, slots=True)
class PythonInstructionEmitter:
    """Emit a Python instruction from a stable callable reference."""

    kind: str = PYTHON_INSTRUCTION_KIND

    def emit(
        self, plan: PythonReference, context: Any = None,
    ) -> InstructionDTO:
        """Return the Python instruction naming ``plan``'s callable."""
        from ..._private.instructions import python

        return python.PythonInstructionEmitter(kind=self.kind).emit(plan, context)


__all__ = ["PythonInstructionEmitter"]
