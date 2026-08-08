"""Edit-time code-generation public API."""

from .decorator import generated
from .discovery import discover, discover_file
from .engine import GenerationSession, generate
from .models import (
    DiscoveredGeneration,
    GeneratedAnnotation,
    GeneratedClass,
    GeneratedField,
    GeneratedFieldKind,
    GeneratedMember,
    GeneratedModule,
    GenerationAction,
    GenerationActionKind,
    GenerationError,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    ProviderGenerationConfig,
)
from .providers import Provider, ProviderContext
from .watcher import FileChange, FileChangeKind, watch

__all__ = [
    "DiscoveredGeneration", "FileChange", "FileChangeKind",
    "GeneratedAnnotation", "GeneratedClass", "GeneratedField", "GeneratedFieldKind", "GeneratedMember", "GeneratedModule",
    "GenerationAction", "GenerationActionKind",
    "GenerationError", "GenerationRequest", "GenerationResult", "GenerationSession", "GenerationStatus", "Provider",
    "ProviderContext", "ProviderGenerationConfig", "discover", "discover_file", "generate", "generated", "watch",
]
