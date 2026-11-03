"""Framework-internal interface of the distribution package."""
from __future__ import annotations

from .adapters import KernelModule
from .dto import (
    AggregateInstructionDTO,
    CoreInstructionDTO,
    DeclaredColumnDTO,
    DeclaredPathDTO,
    InstructionDTO,
    RelationInstructionDTO,
    SourceRelationInstructionDTO,
    decode_core_instruction,
    decode_instruction,
    declared_column_type,
    encode_declared_column,
    encode_instruction,
    instruction_document,
)
from .model import Module
from .service import module_configuration_json, register_module

__all__ = [
    "AggregateInstructionDTO",
    "CoreInstructionDTO",
    "DeclaredColumnDTO",
    "DeclaredPathDTO",
    "InstructionDTO",
    "KernelModule",
    "Module",
    "RelationInstructionDTO",
    "SourceRelationInstructionDTO",
    "decode_core_instruction",
    "decode_instruction",
    "declared_column_type",
    "encode_declared_column",
    "encode_instruction",
    "instruction_document",
    "module_configuration_json",
    "register_module",
]
