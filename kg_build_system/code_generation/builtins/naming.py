"""Deterministic names and path identities for inferred declarations."""
from __future__ import annotations

from dataclasses import dataclass, replace
import keyword
from pathlib import PurePosixPath
import re

from ..ir import (
    GeneratedArrayType, GeneratedClass, GeneratedNullableType, GeneratedStructType,
    GeneratedType,
)
from .formats import PARQUET_LIST_WRAPPERS


def identifier(value: str, *, fallback: str = "field") -> str:
    """A stable Python identifier for a source name."""
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    result = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", result).lower().strip("_") or fallback
    if result[0].isdigit():
        result = f"{fallback}_{result}"
    if keyword.iskeyword(result) or result == "options":
        result += "_"
    return result


def class_part(value: str) -> str:
    """A stable class-name fragment for a source name."""
    words = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    result = "".join(part[:1].upper() + part[1:] for part in words) or "Relation"
    return f"Relation{result}" if result[0].isdigit() else result


def table_class_name(relation: str) -> str:
    return f"{class_part(relation)}Table"


def group_class_name(path: tuple[str, ...], request_id: str) -> str:
    return f"{''.join(class_part(part) for part in path) or class_part(request_id)}TableGroup"


@dataclass(frozen=True, slots=True)
class Paths:
    """The two path forms one inferred member is recorded under.

    ``schema`` names every Parquet node, including the ``list``/``element``
    wrappers, which is the form ``parquet_metadata()`` reports in
    ``path_in_schema``; ``logical`` drops them, which is the form a report shows
    an author.
    """

    schema: tuple[str, ...]
    logical: tuple[str, ...]

    def child(self, *parts: str) -> "Paths":
        return Paths((*self.schema, *parts), (*self.logical, *parts))

    @property
    def schema_text(self) -> str:
        return ".".join(self.schema)

    @property
    def logical_text(self) -> str:
        return ".".join(self.logical)


def top_level_column(paths: Paths) -> str | None:
    """The column a member is, when it is one, since only a column can be promoted."""
    return paths.logical[0] if len(paths.logical) == 1 else None


def record_name(paths: Paths) -> str:
    """The class name of the record derived from the members at this path.

    Shortest-honest naming: the name joins the member-path parts, minus the
    list wrappers, plus one ``Struct`` suffix. Records are named inside their
    relation — ``TimeseriesStruct`` in each table's own file — and may repeat
    across a package's files, because a generated reference resolves inside
    its own file first.
    """
    stem = "".join(
        class_part(part) for part in paths.logical if part not in PARQUET_LIST_WRAPPERS
    )
    return f"{stem}Struct"


def bind_records(classes: tuple[GeneratedClass, ...], in_file: PurePosixPath) -> tuple[GeneratedClass, ...]:
    """Bind every struct reference in these classes to their declaring file.

    Inferred records are emitted alongside their users, so each reference can
    name its target's file exactly: identity is ``(name, file)``, and several
    relations may render records of the same name without the package having
    to tell them apart by name alone.
    """

    def bind(value: GeneratedType) -> GeneratedType:
        if isinstance(value, GeneratedStructType):
            return replace(value, in_file=in_file)
        if isinstance(value, GeneratedArrayType):
            return replace(value, item=bind(value.item))
        if isinstance(value, GeneratedNullableType):
            return replace(value, value=bind(value.value))
        return value

    return tuple(
        replace(
            declaration,
            fields=tuple(
                replace(field, value_type=bind(field.value_type))
                for field in declaration.fields
            ),
        )
        for declaration in classes
    )


__all__ = [
    "Paths", "bind_records", "class_part", "group_class_name", "identifier",
    "record_name", "table_class_name", "top_level_column",
]
