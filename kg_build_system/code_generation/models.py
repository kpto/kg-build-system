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


class GeneratedFieldKind(StrEnum):
    SCALAR = "scalar"
    STRUCT = "struct"
    COLLECTION = "collection"


@dataclass(frozen=True, slots=True)
class GeneratedAnnotation:
    import_module: str
    class_name: str
    arguments: dict[str, StaticValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GeneratedField:
    python_name: str
    external_name: str
    kind: GeneratedFieldKind
    value_type: str
    nullable: bool = False
    item_nullable: bool = False
    description: str | None = None
    annotations: tuple[GeneratedAnnotation, ...] = ()


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
class GeneratedPackage:
    files: tuple[GeneratedFile, ...]


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
    DECLARATION = "declaration"
    DEPENDENCY = "dependency"


@dataclass(frozen=True, slots=True)
class GenerationAction:
    """A watched input change and the declaration modules affected by it."""

    kind: GenerationActionKind
    trigger_path: Path
    source_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class GenerationResult:
    status: GenerationStatus
    changed_paths: tuple[Path, ...] = ()
    diagnostics: tuple[str, ...] = ()
    actions: tuple[GenerationAction, ...] = ()


class GenerationError(ValueError):
    """A source-located, actionable generation failure."""
