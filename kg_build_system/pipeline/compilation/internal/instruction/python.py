"""Python instruction emission.

A Python instruction is a stable reference: module, qualified name and signature.
It is not a live callable and carries no runtime state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ....contract.public import InstructionDTO
from .model import PythonReference


@dataclass(frozen=True, slots=True)
class PythonInstructionEmitter:
    """Emit a Python instruction from a stable callable reference."""

    kind: str = "python"

    def emit(
        self, plan: PythonReference, context: Any = None,
    ) -> InstructionDTO:
        """Return the Python instruction naming ``plan``'s callable."""
        return InstructionDTO(kind=self.kind, payload={
            "module": plan.module,
            "qualname": plan.qualname,
            "signature": plan.signature,
        })


__all__ = ["PythonInstructionEmitter"]
