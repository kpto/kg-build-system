"""Framework-internal and provider interface of edit-time generation.

A generation provider is an extension author: it implements ``Provider`` and
builds the ``Generated*`` tree here. A graph author requests a generation
through the names re-exported by :mod:`kg_build_system.code_generation`; the
generated-declaration IR is :mod:`kg_build_system.code_generation.ir`.
"""
from __future__ import annotations

from .command import add_generate_command
from .discovery import discover, discover_file
from .engine import GenerationSession, generate
from .ir import (
    GeneratedAnnotation,
    GeneratedArrayType,
    GeneratedClass,
    GeneratedField,
    GeneratedFile,
    GeneratedMember,
    GeneratedNullableType,
    GeneratedPackage,
    GeneratedScalarType,
    GeneratedStructType,
    GeneratedType,
    NullabilityNote,
)
from .models import (
    DiscoveredGeneration,
    Generation,
    GenerationAction,
    GenerationActionKind,
    GenerationError,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    Nullability,
    ProviderGenerationConfig,
)
from .providers import Provider, ProviderContext, load_provider, resolve_provider_path
from .requests import generation
from .watcher import FileChange, FileChangeKind, watch

__all__ = [
    "DiscoveredGeneration",
    "add_generate_command",
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
    "GenerationResult",
    "GenerationSession",
    "GenerationStatus",
    "NullabilityNote",
    "GenerationAction",
    "GenerationActionKind",
    "GenerationRequest",
    "Nullability",
    "Provider",
    "ProviderContext",
    "ProviderGenerationConfig",
    "discover",
    "discover_file",
    "generate",
    "generation",
    "load_provider",
    "resolve_provider_path",
    "watch",
]
