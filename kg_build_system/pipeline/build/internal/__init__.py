"""Framework-internal interface of the build package.

The contract reader, instruction dispatch, engine and runtime are internal. The
author-facing surface is :mod:`kg_build_system.pipeline.build.public`.
"""
from __future__ import annotations

from .contract import (
    BuildContract,
    ContractStep,
    ContractWorkflow,
    Instruction,
    read_contract,
)
from .instructions import (
    InstructionDispatcher,
    InstructionExecutor,
    UnknownInstructionKind,
    instruction_payload,
)

__all__ = [
    "BuildContract",
    "ContractStep",
    "ContractWorkflow",
    "Instruction",
    "InstructionDispatcher",
    "InstructionExecutor",
    "UnknownInstructionKind",
    "instruction_payload",
    "read_contract",
]
