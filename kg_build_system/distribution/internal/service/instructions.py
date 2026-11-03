"""Stable Python instruction references for distribution module executors."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ....pipeline.contract.public import InstructionDTO as ContractInstructionDTO
from ..dto.instruction_dto import (
    CoreInstructionDTO,
    InstructionDTO,
    decode_instruction,
    instruction_document,
)


def python_instruction(
    module: str,
    qualname: str,
    inner: InstructionDTO | CoreInstructionDTO,
) -> ContractInstructionDTO:
    """Wrap one module instruction in a stable Python executor reference."""
    return ContractInstructionDTO(
        kind="python",
        payload={
            "module": module,
            "qualname": qualname,
            "instruction": instruction_document(inner),
        },
    )


def nested_instruction(value: Any) -> InstructionDTO:
    """Read the module instruction carried by a Python instruction payload."""
    payload = getattr(value, "payload", value)
    if not isinstance(payload, Mapping):
        raise ValueError("a python instruction requires an object payload")
    nested = payload.get("instruction")
    return decode_instruction(nested)


__all__ = ["nested_instruction", "python_instruction"]
