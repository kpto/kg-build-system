"""Public, provider-independent edit-time generated-package models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict
type StaticValue = str | int | float | bool | None | list[StaticValue] | tuple[StaticValue, ...] | dict[str, StaticValue]


class ProviderGenerationConfig(BaseModel):
    """Immutable, keyword-only configuration owned by a generation provider."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Nullability(StrEnum):
    """How far a declared non-nullability is trusted, per source tier."""

    DECLARED = "declared"
    ENFORCED = "enforced"
    DEFAULTED = "defaulted"


class ScalarTypeName(StrEnum):
    """Scalar names the public authoring surface understands.

    These are the canonical unit types of ``kg_build_system.types``; a name here
    is rendered as its representative type, which is what an author annotates.
    """

    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    DATE = "date"
    TIME = "time"
    TIMESTAMP = "timestamp"
    UUID = "uuid"


ConfigT = TypeVar("ConfigT", bound=ProviderGenerationConfig)


@dataclass(frozen=True, slots=True)
class Generation(Generic[ConfigT]):
    """An inert, typed edit-time generation request."""

    provider: type[object]
    configuration: ConfigT


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """A statically discovered request attached to one public declaration."""

    provider_module: str
    provider_qualname: str
    config_module: str
    config_qualname: str
    configuration: dict[str, StaticValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationLocation:
    project_root: Path
    source_path: Path
    line: int
    column: int
    request_id: str
    source_package: str


@dataclass(frozen=True, slots=True)
class DiscoveredGeneration:
    request: GenerationRequest
    location: GenerationLocation
    product_path: Path
    package_import: str


@dataclass(frozen=True, slots=True)
class GeneratedScalarType:
    """A portable scalar name understood by the public authoring surface."""

    name: str


@dataclass(frozen=True, slots=True)
class GeneratedStructType:
    """A reference to another declaration in the generated package."""

    declaration_name: str


@dataclass(frozen=True, slots=True)
class GeneratedArrayType:
    item: "GeneratedType"


@dataclass(frozen=True, slots=True)
class GeneratedNullableType:
    value: "GeneratedType"


type GeneratedType = (
    GeneratedScalarType | GeneratedStructType | GeneratedArrayType | GeneratedNullableType
)


@dataclass(frozen=True, slots=True)
class GeneratedAnnotation:
    import_module: str
    class_name: str
    arguments: dict[str, StaticValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GeneratedField:
    python_name: str
    external_name: str
    value_type: GeneratedType
    description: str | None = None
    annotations: tuple[GeneratedAnnotation, ...] = ()
    nullability: Nullability = Nullability.DEFAULTED
    schema_path: str = ""
    logical_path: str = ""


@dataclass(frozen=True, slots=True)
class GeneratedMember:
    """A named declaration pointer carried by a generated table group."""

    python_name: str
    declaration_name: str


@dataclass(frozen=True, slots=True)
class GeneratedClass:
    name: str
    fields: tuple[GeneratedField, ...] = ()
    members: tuple[GeneratedMember, ...] = ()
    description: str | None = None
    base: str | None = None
    declaration_name: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    """One normalized Python file inside a generated package."""

    relative_path: Path
    declarations: tuple[GeneratedClass, ...] = ()
    exports: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NullabilityNote:
    """One rendered provenance line about where a shape's nullability came from.

    ``sources`` names the physical inputs the line describes and ``declarations``
    the declarations derived from them, so a catalogue rendered one file per table
    carries only the lines about its own source.
    """

    line: str
    sources: tuple[str, ...] = ()
    declarations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratedPackage:
    files: tuple[GeneratedFile, ...]
    nullability_notes: tuple[NullabilityNote, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationManifest:
    format_version: str
    request_id: str
    request_source_package: str
    provider_import: str
    provider_qualname: str
    provider_version: str
    request_fingerprint: str
    owned_files: tuple[str, ...]
    owned_directories: tuple[str, ...]
    owned_file_hashes: dict[str, str] = field(default_factory=dict)


class GenerationStatus(StrEnum):
    CURRENT = "current"
    CHANGED = "changed"
    STALE = "stale"


class GenerationActionKind(StrEnum):
    DECLARATION_ADDED = "declaration_added"
    DECLARATION_CHANGED = "declaration_changed"
    DECLARATION_DELETED = "declaration_deleted"
    DEPENDENCY = "dependency"


@dataclass(frozen=True, slots=True)
class GenerationAction:
    """A watched input change and the declaration modules affected by it."""

    kind: GenerationActionKind
    trigger_path: Path
    source_paths: tuple[Path, ...]
    declaration_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    status: GenerationStatus
    changed_paths: tuple[Path, ...] = ()
    created_paths: tuple[Path, ...] = ()
    updated_paths: tuple[Path, ...] = ()
    deleted_paths: tuple[Path, ...] = ()
    diagnostics: tuple[str, ...] = ()
    actions: tuple[GenerationAction, ...] = ()


class GenerationError(ValueError):
    """A source-located, actionable generation failure."""
