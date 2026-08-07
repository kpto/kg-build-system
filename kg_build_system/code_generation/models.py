"""Public, provider-independent edit-time code-generation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, ConfigDict
type StaticValue = str | int | float | bool | None | list[StaticValue] | tuple[StaticValue, ...] | dict[str, StaticValue]


class ProviderGenerationConfig(BaseModel):
    """Immutable, keyword-only configuration owned by a generation provider."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


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
    class_name: str


@dataclass(frozen=True, slots=True)
class DiscoveredGeneration:
    request: GenerationRequest
    location: GenerationLocation
    sidecar_path: Path
    generated_name: str


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
class GeneratedClass:
    name: str
    fields: tuple[GeneratedField, ...]
    description: str | None = None
    base: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedModule:
    classes: tuple[GeneratedClass, ...]


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
