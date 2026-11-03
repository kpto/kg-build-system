"""The instruction-emitter protocol."""
from __future__ import annotations

from typing import Any, Protocol

from .....contract.model.public import InstructionDTO


class InstructionEmitter(Protocol):
    """Turn one engine-neutral plan into the instruction a step owns."""

    kind: str

    def emit(self, plan: Any, context: Any) -> InstructionDTO:
        """Return the instruction for ``plan`` under ``context``."""
        ...


__all__ = ["InstructionEmitter"]
