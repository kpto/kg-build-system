"""Request, discovery, ownership and result models for edit-time generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Generic, TypeVar

from .ir import (
    GeneratedAnnotation, GeneratedArrayType, GeneratedClass, GeneratedField,
    GeneratedFile, GeneratedMember, GeneratedNullableType, GeneratedPackage,
    GeneratedScalarType, GeneratedStructType, GeneratedType, Nullability,
    NullabilityNote, ScalarTypeName, StaticValue,
)
from .providers import ProviderGenerationConfig

ConfigT = TypeVar("ConfigT", bound=ProviderGenerationConfig)


@dataclass(frozen=True, slots=True)
class Generation(Generic[ConfigT]):
    """An inert, typed edit-time generation request.

    Create it with :func:`kg_build_system.code_generation.generation`; the
    assignment name is the request identity. It holds a provider class and its
    validated configuration, and performs no observation or writes.

    Example:
        ```python
        from kg_build_system.code_generation import generation
        from kg_build_system.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        people = generation(
            InferDataContractProvider,
            DataContractInferenceConfig(
                source="../data/people.csv", mode="table",
            ),
        )
        ```
    """

    provider: type[object]
    configuration: ConfigT


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """A statically discovered request attached to one public declaration.

    The provider and configuration are stored as import coordinates, so
    discovery never imports the author-owned package. ``configuration`` holds
    the static literal keyword arguments, validated into the provider's
    ``CONFIG_TYPE`` when generation runs.

    Example:
        ```python
        from kg_build_system.code_generation import GenerationRequest

        request = GenerationRequest(
            "project.providers", "PeopleProvider",
            "project.providers", "PeopleConfiguration",
            {"source": "../data/people.csv"},
        )
        ```
    """

    provider_module: str
    provider_qualname: str
    config_module: str
    config_qualname: str
    configuration: dict[str, StaticValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationLocation:
    """Where one request was declared and the identity it received.

    ``project_root`` and ``source_path`` locate the author-owned ``__init__.py``;
    ``line`` and ``column`` point at the assignment. ``request_id`` is the
    assignment name, and ``source_package`` is the package containing it.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.code_generation.interfaces import GenerationLocation

        location = GenerationLocation(
            Path("."), Path("contracts/__init__.py"), 4, 1,
            "people", "contracts",
        )
        ```
    """

    project_root: Path
    source_path: Path
    line: int
    column: int
    request_id: str
    source_package: str


@dataclass(frozen=True, slots=True)
class DiscoveredGeneration:
    """One request, its location, and the product it owns.

    ``product_path`` is the sibling directory of the author-owned
    ``__init__.py``; ``package_import`` is the import name of the generated
    package.

    Example:
        ```python
        from kg_build_system.code_generation import discover

        request = discover(".")[0]
        request.product_path, request.package_import
        ```
    """

    request: GenerationRequest
    location: GenerationLocation
    product_path: Path
    package_import: str


@dataclass(frozen=True, slots=True)
class GenerationManifest:
    """The ownership record stored in a product's ``.kbs-generation.json``.

    The request fingerprint covers the declaration, configuration, provider
    identity and format version; ``source_digest`` is provider provenance only.
    ``owned_files`` and ``owned_directories`` are normalized relative POSIX
    paths.

    Example:
        ```python
        from kg_build_system.code_generation import discover

        product = discover(".")[0].product_path
        manifest_path = product / ".kbs-generation.json"
        ```
    """

    format_version: str
    request_id: str
    request_source_package: str
    provider_import: str
    provider_qualname: str
    provider_version: str
    request_fingerprint: str
    source_digest: str | None
    owned_files: tuple[str, ...]
    owned_directories: tuple[str, ...]
    owned_file_hashes: dict[str, str] = field(default_factory=dict)


class GenerationStatus(StrEnum):
    """The outcome of comparing a desired product with what is installed.

    ``CURRENT`` means no product needs writing; ``CHANGED`` means the desired
    state differs and was written (or would be written); ``STALE`` is reported
    by ``check`` when products are missing, altered or orphaned.

    Example:
        ```python
        import asyncio

        from kg_build_system.code_generation import generate

        result = asyncio.run(generate(".", check=True))
        result.status in {"current", "stale"}
        ```
    """

    CURRENT = "current"
    CHANGED = "changed"
    STALE = "stale"


class GenerationActionKind(StrEnum):
    """The kind of declaration change observed by watch mode.

    Example:
        ```python
        from kg_build_system.code_generation.interfaces import (
            GenerationActionKind,
        )

        GenerationActionKind.DECLARATION_ADDED
        ```
    """

    DECLARATION_ADDED = "declaration_added"
    DECLARATION_CHANGED = "declaration_changed"
    DECLARATION_DELETED = "declaration_deleted"


@dataclass(frozen=True, slots=True)
class GenerationAction:
    """A watched input change and the declaration modules affected by it.

    ``source_paths`` are the declaration files to regenerate;
    ``declaration_id`` is the generated package import when the action concerns
    one request.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.code_generation.interfaces import (
            GenerationAction, GenerationActionKind,
        )

        action = GenerationAction(
            GenerationActionKind.DECLARATION_ADDED,
            Path("contracts/__init__.py"),
            (Path("contracts/__init__.py"),),
            "contracts.people",
        )
        ```
    """

    kind: GenerationActionKind
    trigger_path: Path
    source_paths: tuple[Path, ...]
    declaration_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """The outcome of one generation or check pass.

    Paths are relative to the project root. ``actions`` is populated by watch
    mode; ``diagnostics`` explains a ``STALE`` or failed comparison.

    Example:
        ```python
        import asyncio

        from kg_build_system.code_generation import generate

        result = asyncio.run(generate("."))
        result.created_paths
        ```
    """

    status: GenerationStatus
    changed_paths: tuple[Path, ...] = ()
    created_paths: tuple[Path, ...] = ()
    updated_paths: tuple[Path, ...] = ()
    deleted_paths: tuple[Path, ...] = ()
    diagnostics: tuple[str, ...] = ()
    actions: tuple[GenerationAction, ...] = ()


class GenerationError(ValueError):
    """A source-located, actionable generation failure.

    It extends ``ValueError``; the message names the request file and line when
    the defect comes from discovery.

    Example:
        ```python
        from kg_build_system.code_generation import GenerationError

        isinstance(GenerationError("contracts/__init__.py:4: invalid request"), ValueError)
        ```
    """


__all__ = [
    "DiscoveredGeneration", "GeneratedAnnotation", "GeneratedArrayType",
    "GeneratedClass", "GeneratedField", "GeneratedFile", "GeneratedMember",
    "GeneratedNullableType", "GeneratedPackage", "GeneratedScalarType",
    "GeneratedStructType", "GeneratedType", "Generation", "GenerationAction",
    "GenerationActionKind", "GenerationError", "GenerationLocation",
    "GenerationManifest", "GenerationRequest", "GenerationResult",
    "GenerationStatus", "Nullability", "NullabilityNote",
    "ProviderGenerationConfig", "ScalarTypeName", "StaticValue",
]
