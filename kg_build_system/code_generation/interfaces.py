"""Framework-internal and provider interface of edit-time generation.

A generation provider is an extension author: it implements ``Provider`` and
builds the ``Generated*`` tree in :mod:`kg_build_system.code_generation.ir`. A
graph author requests a generation through the names re-exported by
:mod:`kg_build_system.code_generation`.
"""
from __future__ import annotations

from .command import add_generate_command
from .discovery import discover, discover_file
from .engine import GenerationSession, generate
from .ir import (
    GeneratedAnnotation, GeneratedArrayType, GeneratedClass, GeneratedField,
    GeneratedFile, GeneratedMember, GeneratedNullableType, GeneratedPackage,
    GeneratedScalarType, GeneratedStructType, GeneratedType, Nullability,
    NullabilityNote, ScalarTypeName, StaticValue,
)
from .models import (
    DiscoveredGeneration, Generation, GenerationAction, GenerationActionKind,
    GenerationError, GenerationLocation, GenerationManifest, GenerationRequest,
    GenerationResult, GenerationStatus,
)
from .providers import (
    Provider, ProviderContext, ProviderGenerationConfig, load_provider,
    resolve_provider_path,
)
from .requests import generation
from .watcher import FileChange, FileChangeKind, watch

__all__ = [
    "DiscoveredGeneration",
    "FileChange",
    "FileChangeKind",
    "GeneratedAnnotation",
    "GeneratedArrayType",
    "GeneratedClass",
    "GeneratedField",
    "GeneratedFile",
    "GeneratedMember",
    "GeneratedNullableType",
    "GeneratedPackage",
    "GeneratedScalarType",
    "GeneratedStructType",
    "GeneratedType",
    "Generation",
    "GenerationAction",
    "GenerationActionKind",
    "GenerationError",
    "GenerationLocation",
    "GenerationManifest",
    "GenerationRequest",
    "GenerationResult",
    "GenerationSession",
    "GenerationStatus",
    "Nullability",
    "NullabilityNote",
    "Provider",
    "ProviderContext",
    "ProviderGenerationConfig",
    "ScalarTypeName",
    "StaticValue",
    "add_generate_command",
    "discover",
    "discover_file",
    "generate",
    "generation",
    "load_provider",
    "resolve_provider_path",
    "watch",
]
