"""Module-produced IR.

A module compiles its steps into frozen instruction documents; the executor
reads them at execution time. They carry no behaviour and no owner. Core's
instructions are owned here; target instructions are re-exported when the target
is installed.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .core.ir import (
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

if TYPE_CHECKING:
    from .targets.meta_graph.ir import (
        MetaGraphBindingIR,
        MetaGraphComponentIR,
        MetaGraphDocumentIR,
        MetaGraphEndpointIR,
        MetaGraphPropertyIR,
        decode_meta_graph_instruction,
        encode_meta_graph_instruction,
    )
    from .targets.neo4j.ir import (
        Neo4jComponentImportIR,
        Neo4jEdgeImportIR,
        Neo4jExportInstructionIR,
        Neo4jInstructionIR,
        Neo4jNodeImportIR,
        Neo4jScriptInstructionIR,
        decode_neo4j_instruction,
        encode_neo4j_instruction,
    )


_TARGET_IR_EXPORTS: dict[str, tuple[str, str]] = {
    "MetaGraphBindingIR": (".targets.meta_graph.ir", "MetaGraphBindingIR"),
    "MetaGraphComponentIR": (".targets.meta_graph.ir", "MetaGraphComponentIR"),
    "MetaGraphDocumentIR": (".targets.meta_graph.ir", "MetaGraphDocumentIR"),
    "MetaGraphEndpointIR": (".targets.meta_graph.ir", "MetaGraphEndpointIR"),
    "MetaGraphPropertyIR": (".targets.meta_graph.ir", "MetaGraphPropertyIR"),
    "decode_meta_graph_instruction": (
        ".targets.meta_graph.ir", "decode_meta_graph_instruction",
    ),
    "encode_meta_graph_instruction": (
        ".targets.meta_graph.ir", "encode_meta_graph_instruction",
    ),
    "Neo4jComponentImportIR": (".targets.neo4j.ir", "Neo4jComponentImportIR"),
    "Neo4jEdgeImportIR": (".targets.neo4j.ir", "Neo4jEdgeImportIR"),
    "Neo4jExportInstructionIR": (".targets.neo4j.ir", "Neo4jExportInstructionIR"),
    "Neo4jInstructionIR": (".targets.neo4j.ir", "Neo4jInstructionIR"),
    "Neo4jNodeImportIR": (".targets.neo4j.ir", "Neo4jNodeImportIR"),
    "Neo4jScriptInstructionIR": (".targets.neo4j.ir", "Neo4jScriptInstructionIR"),
    "decode_neo4j_instruction": (
        ".targets.neo4j.ir", "decode_neo4j_instruction",
    ),
    "encode_neo4j_instruction": (
        ".targets.neo4j.ir", "encode_neo4j_instruction",
    ),
}

__all__ = [
    "AggregateInstructionIR",
    "CoreInstructionIR",
    "CoreStepInstructionIR",
    "DeclaredColumnIR",
    "DeclaredPathIR",
    "MetaGraphBindingIR",
    "MetaGraphComponentIR",
    "MetaGraphDocumentIR",
    "MetaGraphEndpointIR",
    "MetaGraphPropertyIR",
    "Neo4jComponentImportIR",
    "Neo4jEdgeImportIR",
    "Neo4jExportInstructionIR",
    "Neo4jInstructionIR",
    "Neo4jNodeImportIR",
    "Neo4jScriptInstructionIR",
    "RelationInstructionIR",
    "SourceRelationInstructionIR",
    "decode_core_instruction",
    "decode_meta_graph_instruction",
    "decode_neo4j_instruction",
    "declared_column_type",
    "encode_core_instruction",
    "encode_declared_column",
    "encode_meta_graph_instruction",
    "encode_neo4j_instruction",
]


def __getattr__(name: str) -> Any:
    target = _TARGET_IR_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(
        import_module(module_name, __package__), attribute,
    )
    globals()[name] = value
    return value
