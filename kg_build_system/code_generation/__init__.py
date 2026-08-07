"""Edit-time code-generation public API."""

from .decorator import generated
from .discovery import discover, discover_file
from .dummy import DummyProvider
from .engine import GenerationSession, generate
from .models import (
    DiscoveredGeneration,
    GeneratedAnnotation,
    GeneratedClass,
    GeneratedField,
    GeneratedFieldKind,
    GeneratedModule,
    GenerationError,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
)
from .providers import CodeGenerationProvider, ProviderContext, get_provider, register_provider
from .watcher import FileChange, FileChangeKind, watch

register_provider(DummyProvider(), replace=True)

__all__ = [
    "CodeGenerationProvider", "DiscoveredGeneration", "DummyProvider", "FileChange", "FileChangeKind",
    "GeneratedAnnotation", "GeneratedClass", "GeneratedField", "GeneratedFieldKind", "GeneratedModule",
    "GenerationError", "GenerationRequest", "GenerationResult", "GenerationSession", "GenerationStatus", "ProviderContext",
    "discover", "discover_file", "generate", "generated", "get_provider", "register_provider", "watch",
]
