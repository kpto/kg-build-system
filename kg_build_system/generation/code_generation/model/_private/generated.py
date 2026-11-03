"""Generated-declaration render model.

A provider returns this tree. It states what to render, not how to render it;
rendering is an engine concern and lives in
:mod:`kg_build_system.generation.code_generation.service._private.rendering`.
Every value is frozen data with no owner, connection or behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath

from ..public.values import StaticValue


class Nullability(StrEnum):
    """How far a declared non-nullability is trusted, per source tier."""

    DECLARED = "declared"
    ENFORCED = "enforced"
    DEFAULTED = "defaulted"


class ScalarTypeName(StrEnum):
    """Scalar names the public authoring surface understands."""

    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    DATE = "date"
    TIME = "time"
    TIMESTAMP = "timestamp"
    UUID = "uuid"


@dataclass(frozen=True, slots=True)
class GeneratedScalarType:
    """A portable scalar name understood by the public authoring surface."""

    name: str


@dataclass(frozen=True, slots=True)
class GeneratedStructType:
    """A reference to another declaration in the generated package.

    ``in_file`` binds the reference to the file that declares its target, so
    identity is ``(name, file)`` and several files may declare same-named
    records. An unbound reference resolves at render time by the local-first,
    package-unique rule.
    """

    declaration_name: str
    in_file: PurePosixPath | None = None


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
    #: Provider-computed digest of the observed source schema. It is provenance
    #: recorded in the manifest, never a tracked input: the engine does not
    #: interpret it and its change alone does not invalidate a product.
    source_digest: str | None = None


__all__ = [
    "GeneratedAnnotation", "GeneratedArrayType", "GeneratedClass",
    "GeneratedField", "GeneratedFile", "GeneratedMember",
    "GeneratedNullableType", "GeneratedPackage", "GeneratedScalarType",
    "GeneratedStructType", "GeneratedType", "Nullability", "NullabilityNote",
    "ScalarTypeName", "StaticValue",
]
