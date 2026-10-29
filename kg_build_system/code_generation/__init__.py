"""Author-facing edit-time generation requests.

A graph author declares ``generation(...)`` and runs ``kbs generate`` or
``generate``/``watch`` here. The provider extension contract is
:mod:`kg_build_system.code_generation.interfaces`; the generated-declaration IR
is :mod:`kg_build_system.code_generation.ir`.
"""
from __future__ import annotations

from .discovery import discover, discover_file
from .engine import GenerationSession, generate
from .models import (
    Generation,
    GenerationError,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
)
from .requests import generation
from .watcher import FileChange, FileChangeKind, watch

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
