"""Container for upstream generation systems.

The edit-time code-generation system lives in
:mod:`kg_build_system.generation.code_generation`. Its author-facing names are
re-exported here for the canonical ``kg_build_system.generation`` import.
"""
from __future__ import annotations

from .code_generation import (
    AssetContractOptions, FileChange, FileChangeKind, GenerationError,
    GenerationRequest, GenerationResult, GenerationSession, GenerationStatus,
    asset_contract, discover, discover_file, generate, watch,
)

__all__ = [
    "AssetContractOptions",
    "FileChange",
    "FileChangeKind",
    "GenerationError",
    "GenerationRequest",
    "GenerationResult",
    "GenerationSession",
    "GenerationStatus",
    "asset_contract",
    "discover",
    "discover_file",
    "generate",
    "watch",
]
