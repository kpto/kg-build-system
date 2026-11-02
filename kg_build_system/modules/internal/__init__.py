"""Internal module protocol, registration values and instruction IR."""
from __future__ import annotations

from .ir import (
    AggregateInstructionIR,
    CoreInstructionIR,
    CoreStepInstructionIR,
    DeclaredColumnIR,
    DeclaredPathIR,
    RelationInstructionIR,
    SourceRelationInstructionIR,
    decode_core_instruction,
    declared_column_type,
    encode_core_instruction,
    encode_declared_column,
)
from .module import Module, ModuleRegistration, ModuleRegistrationConfiguration
from .registration import module_configuration_json, register_module

__all__ = [
    "AggregateInstructionIR",
    "CoreInstructionIR",
    "CoreStepInstructionIR",
    "DeclaredColumnIR",
    "DeclaredPathIR",
    "Module",
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "RelationInstructionIR",
    "SourceRelationInstructionIR",
    "decode_core_instruction",
    "declared_column_type",
    "encode_core_instruction",
    "encode_declared_column",
    "module_configuration_json",
    "register_module",
]
