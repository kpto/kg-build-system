"""Module-produced IR.

A module compiles its steps into these frozen instruction documents; the core
module reads them at execution time. They carry no behavior and no owner.
"""
from __future__ import annotations

from .core.ir import (
    AggregateInstructionIR,
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
from .targets.meta_graph.ir import (
    MetaGraphBindingIR,
    MetaGraphComponentIR,
    MetaGraphDocumentIR,
    MetaGraphEndpointIR,
    MetaGraphPropertyIR,
    decode_meta_graph_instruction,
    encode_meta_graph_instruction,
)

__all__ = [
    "AggregateInstructionIR",
    "CoreStepInstructionIR",
    "DeclaredColumnIR",
    "DeclaredPathIR",
    "MetaGraphBindingIR",
    "MetaGraphComponentIR",
    "MetaGraphDocumentIR",
    "MetaGraphEndpointIR",
    "MetaGraphPropertyIR",
    "RelationInstructionIR",
    "SourceRelationInstructionIR",
    "decode_core_instruction",
    "declared_column_type",
    "decode_meta_graph_instruction",
    "encode_core_instruction",
    "encode_declared_column",
    "encode_meta_graph_instruction",
]
