"""Author-facing edit-time generation requests and run surface.

A graph author declares ``generation(...)`` and runs ``kbs generate`` or
``generate``/``watch`` here. The provider extension contract is
:mod:`kg_build_system.generation.code_generation.internal`; the
generated-declaration render model is
:mod:`kg_build_system.generation.code_generation.internal.generated`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .._private.engine import GenerationSession
from .._private.watcher import FileChange, FileChangeKind
from ..internal.models import (
    Generation, GenerationError, GenerationRequest, GenerationResult,
    GenerationStatus,
)
from .requests import generation
from .run import discover, discover_file, generate, watch

if TYPE_CHECKING:
    from ..internal.models import DiscoveredGeneration
    from ..internal.providers import Provider, ProviderGenerationConfig

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
