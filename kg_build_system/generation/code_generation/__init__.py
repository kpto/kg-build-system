"""Author-facing edit-time generation requests.

A graph author declares ``generation(...)`` and runs ``kbs generate`` or
``generate``/``watch`` here. The provider extension contract is
:mod:`kg_build_system.generation.code_generation.model.internal`; the
generated-declaration render model is
:mod:`kg_build_system.generation.code_generation.model._private.generated`.
"""
from __future__ import annotations

from .model.public import (
    FileChange, FileChangeKind, Generation, GenerationError, GenerationRequest,
    GenerationResult, GenerationStatus,
)
from .service.public import (
    GenerationSession, discover, discover_file, generate, generation, watch,
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
