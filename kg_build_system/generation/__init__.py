"""Container for upstream generation systems.

The edit-time code-generation system lives in
:mod:`kg_build_system.generation.code_generation`. Its author-facing names are
re-exported here for the canonical ``kg_build_system.generation`` import.
"""
from __future__ import annotations

from .code_generation import (
    FileChange, FileChangeKind, Generation, GenerationError, GenerationRequest,
    GenerationResult, GenerationSession, GenerationStatus, discover,
    discover_file, generate, generation, watch,
)

__all__ = [
    "FileChange",
    "FileChangeKind",
    "Generation",
    "GenerationError",
    "GenerationRequest",
    "GenerationResult",
    "GenerationSession",
    "GenerationStatus",
    "discover",
    "discover_file",
    "generate",
    "generation",
    "watch",
]
