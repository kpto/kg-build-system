"""Framework-internal interface of the distribution package.

The interface is the module protocol and the instruction DTOs. Registration and
the supplied module implementations are reached through the package facade, and
their mechanisms live in :mod:`kg_build_system.distribution._private`.
"""
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
)
from .model import Module

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
]
