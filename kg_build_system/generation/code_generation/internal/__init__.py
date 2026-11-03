"""Internal generation request models, provider contract and render model."""
from __future__ import annotations

from .adapters.provider import load_provider, resolve_provider_path
from .generated import (
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
    Nullability,
    NullabilityNote,
    ScalarTypeName,
    StaticValue,
)
from .models import (
    DiscoveredGeneration,
    Generation,
    GenerationAction,
    GenerationActionKind,
    GenerationError,
    GenerationLocation,
    GenerationManifest,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
)
from .providers import Provider, ProviderContext, ProviderGenerationConfig

__all__ = [
    "DiscoveredGeneration", "GeneratedAnnotation", "GeneratedArrayType",
    "GeneratedClass", "GeneratedField", "GeneratedFile", "GeneratedMember",
    "GeneratedNullableType", "GeneratedPackage", "GeneratedScalarType",
    "GeneratedStructType", "GeneratedType", "Generation", "GenerationAction",
    "GenerationActionKind", "GenerationError", "GenerationLocation",
    "GenerationManifest", "GenerationRequest", "GenerationResult",
    "GenerationStatus", "Nullability", "NullabilityNote", "Provider",
    "ProviderContext", "ProviderGenerationConfig", "ScalarTypeName",
    "add_generate_command",
    "StaticValue", "load_provider", "resolve_provider_path",
]


def add_generate_command(commands: object) -> None:
    """Register the ``kbs generate`` subcommand on an argparse registry."""
    from .._private.command import add_generate_command as implementation

    implementation(commands)
