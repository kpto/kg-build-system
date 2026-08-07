"""Public, provider-independent edit-time code-generation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
type StaticValue = str | int | float | bool | None | list[StaticValue] | tuple[StaticValue, ...] | dict[str, StaticValue]


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """A statically discovered request attached to one public declaration."""

    provider: str
    source: str
    selector: str | None = None
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


@dataclass(frozen=True, slots=True)
class GenerationResult:
    status: GenerationStatus
    changed_paths: tuple[Path, ...] = ()
    diagnostics: tuple[str, ...] = ()


class GenerationError(ValueError):
    """A source-located, actionable generation failure."""
