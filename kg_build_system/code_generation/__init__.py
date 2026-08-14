"""Edit-time code-generation public API."""

from .requests import generation
from .discovery import discover, discover_file
from .engine import GenerationSession, generate
from .models import (
    DiscoveredGeneration,
    GeneratedAnnotation,
    GeneratedArrayType,
    GeneratedClass,
    GeneratedField,
    GeneratedNullableType,
    GeneratedScalarType,
    GeneratedStructType,
    GeneratedType,
    GeneratedMember, GeneratedFile, GeneratedPackage, Generation,
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
    "GeneratedAnnotation", "GeneratedArrayType", "GeneratedClass", "GeneratedField",
    "GeneratedNullableType", "GeneratedScalarType", "GeneratedStructType",
    "GeneratedType",
    "GeneratedMember", "GeneratedFile", "GeneratedPackage", "Generation",
    "GenerationAction", "GenerationActionKind",
    "GenerationError", "GenerationRequest", "GenerationResult", "GenerationSession", "GenerationStatus", "Provider",
    "ProviderContext", "ProviderGenerationConfig", "discover", "discover_file", "generate", "generation", "watch",
]
