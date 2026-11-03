"""Framework-internal distribution service interface.

Registration, instruction codecs and blueprint context are thin wrappers whose
mechanisms live in :mod:`kg_build_system.distribution.service._private`.
"""
from __future__ import annotations

from .adapters import KernelModule
from .blueprint import blueprint_from_context
from .dto.codec import (
    decode_core_instruction,
    decode_instruction,
    declared_column_type,
    encode_declared_column,
    encode_instruction,
    instruction_document,
)
from .registration import module_configuration_json, register_module

__all__ = [
    "KernelModule",
    "blueprint_from_context",
    "decode_core_instruction",
    "decode_instruction",
    "declared_column_type",
    "encode_declared_column",
    "encode_instruction",
    "instruction_document",
    "module_configuration_json",
    "register_module",
]
