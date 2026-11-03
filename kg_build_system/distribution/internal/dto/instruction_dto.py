"""Instruction DTOs carried by a distribution step.

A step names its instruction as ``InstructionDTO(kind=..., payload=...)``.
Core contributes typed instructions for the three shapes its executor knows;
they encode to the same kind-and-payload form, so a consumer never needs the
typed class to read one.

The DTO is data: it carries no behaviour and no owner. Encoding and decoding are
functions beside it.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Literal, TypeAlias

from pydantic import JsonValue

from ....kernel.internal.json import FrozenObject, thaw_json
from ....kernel.internal.types import type_from_document, type_to_document
from ....kernel.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class InstructionDTO:
    """One step instruction as a discriminator and a JSON payload."""

    kind: str
    payload: JsonValue

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("instruction kind must be a non-empty string")


@dataclass(frozen=True, slots=True)
class DeclaredPathDTO:
    """One declared member path, in both forms the source step needs."""

    schema_path: str
    logical_path: str

    def __post_init__(self) -> None:
        if not self.schema_path:
            raise ValueError("declared schema paths must be non-empty")
        if not self.logical_path:
            raise ValueError("declared logical paths must be non-empty")


@dataclass(frozen=True, slots=True)
class DeclaredColumnDTO:
    """One declared top-level field, with the type it is declared to hold."""

    name: str
    logical_type: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("declared columns require a non-empty name")
        if not isinstance(self.logical_type, Mapping):
            raise ValueError("declared column types must be objects")
        type_from_document(self.logical_type)
        object.__setattr__(self, "logical_type", dict(self.logical_type))


@dataclass(frozen=True, slots=True)
class SourceRelationInstructionDTO:
    """Read one physical source and expose its widened, typed relation."""

    relation: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    declaration: str = ""
    declared_columns: tuple[DeclaredColumnDTO, ...] = ()
    declared_paths: tuple[DeclaredPathDTO, ...] = ()
    kind: Literal["source_relation"] = "source_relation"

    def __post_init__(self) -> None:
        for value, label in (
            (self.relation, "relation"),
            (self.location, "location"),
        ):
            if not value:
                raise ValueError(f"source instructions require a non-empty {label}")
        if self.format not in {"csv", "json", "parquet"}:
            raise ValueError(f"unknown source format {self.format!r}")
        object.__setattr__(self, "declared_columns", tuple(self.declared_columns))
        object.__setattr__(self, "declared_paths", tuple(self.declared_paths))


@dataclass(frozen=True, slots=True)
class RelationInstructionDTO:
    """Define one named relation from SQL the module already emitted."""

    relation: str
    sql: str
    kind: Literal["relation"] = "relation"

    def __post_init__(self) -> None:
        if not self.relation:
            raise ValueError("relation instructions require a non-empty relation")
        if not self.sql:
            raise ValueError("relation instructions require non-empty SQL")


@dataclass(frozen=True, slots=True)
class AggregateInstructionDTO:
    """Union every binding relation of one bound component into graph records."""

    relation: str
    kind: Literal["aggregate"] = "aggregate"

    def __post_init__(self) -> None:
        if not self.relation:
            raise ValueError("aggregate instructions require a non-empty relation")


CoreInstructionDTO: TypeAlias = (
    SourceRelationInstructionDTO | RelationInstructionDTO | AggregateInstructionDTO
)


def declared_column_type(column: DeclaredColumnDTO) -> LogicalTypeDTO:
    """The declared logical type a column DTO carries."""
    return type_from_document(column.logical_type)


def encode_declared_column(
    name: str, logical_type: LogicalTypeDTO,
) -> DeclaredColumnDTO:
    """One declared column, carrying the logical type in its JSON form."""
    return DeclaredColumnDTO(name=name, logical_type=type_to_document(logical_type))


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _plain(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def encode_instruction(
    value: InstructionDTO | CoreInstructionDTO,
) -> InstructionDTO:
    """Return one instruction in its kind-and-payload form."""
    if isinstance(value, InstructionDTO):
        return value
    payload = _plain(value)
    payload.pop("kind", None)
    return InstructionDTO(kind=value.kind, payload=payload)


def instruction_document(
    value: InstructionDTO | CoreInstructionDTO,
) -> dict[str, JsonValue]:
    """Return the JSON-compatible document stored for one step."""
    encoded = encode_instruction(value)
    return {"kind": encoded.kind, "payload": encoded.payload}


def decode_instruction(value: object) -> InstructionDTO:
    """Read one kind-and-payload instruction from its stored form."""
    if isinstance(value, InstructionDTO):
        return value
    if isinstance(
        value,
        (
            SourceRelationInstructionDTO,
            RelationInstructionDTO,
            AggregateInstructionDTO,
        ),
    ):
        return encode_instruction(value)
    if isinstance(value, FrozenObject):
        value = thaw_json(value)
    if not isinstance(value, Mapping):
        raise ValueError("step instructions require an object payload")
    unknown = set(value) - {"kind", "payload"}
    if unknown:
        raise ValueError(
            f"unknown instruction field(s) "
            f"{', '.join(sorted(map(repr, unknown)))}"
        )
    kind = value.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ValueError("step instruction field 'kind' must be a non-empty string")
    if "payload" not in value:
        raise ValueError("step instruction requires a payload")
    return InstructionDTO(kind=kind, payload=value["payload"])


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"source instruction field {key!r} must be a non-empty string")
    return item


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str) or not item:
        raise ValueError(f"source instruction field {key!r} must be a non-empty string")
    return item


def _sequence(value: Any, key: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    raise ValueError(f"source instruction field {key!r} must be a sequence")


def _mapping(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"source instruction field {key!r} must be an object")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], kind: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(
            f"unknown field(s) {', '.join(sorted(map(repr, unknown)))} "
            f"in {kind} instruction"
        )


def _declared_path(value: Any) -> DeclaredPathDTO:
    if isinstance(value, DeclaredPathDTO):
        return value
    data = _mapping(value, "declared_paths")
    _reject_unknown(data, {"schema_path", "logical_path"}, "source_relation")
    return DeclaredPathDTO(
        schema_path=_text(data, "schema_path"),
        logical_path=_text(data, "logical_path"),
    )


def _declared_column(value: Any) -> DeclaredColumnDTO:
    if isinstance(value, DeclaredColumnDTO):
        return value
    data = _mapping(value, "declared_columns")
    _reject_unknown(data, {"name", "logical_type"}, "source_relation")
    return DeclaredColumnDTO(
        name=_text(data, "name"),
        logical_type=dict(_mapping(data.get("logical_type"), "logical_type")),
    )


def _decode_source_relation(
    payload: Mapping[str, Any],
) -> SourceRelationInstructionDTO:
    _reject_unknown(
        payload,
        {
            "relation", "location", "format", "credential_reference",
            "declaration", "declared_columns", "declared_paths",
        },
        "source_relation",
    )
    format_value = payload.get("format")
    if format_value not in {"csv", "json", "parquet"}:
        raise ValueError(f"unknown source format {format_value!r}")
    declaration = payload.get("declaration", "")
    if not isinstance(declaration, str):
        raise ValueError("source instruction field 'declaration' must be a string")
    return SourceRelationInstructionDTO(
        relation=_text(payload, "relation"),
        location=_text(payload, "location"),
        format=format_value,
        credential_reference=_optional_text(payload, "credential_reference"),
        declaration=declaration,
        declared_columns=tuple(
            _declared_column(item)
            for item in _sequence(payload.get("declared_columns"), "declared_columns")
        ),
        declared_paths=tuple(
            _declared_path(item)
            for item in _sequence(payload.get("declared_paths"), "declared_paths")
        ),
    )


def _decode_relation(payload: Mapping[str, Any]) -> RelationInstructionDTO:
    _reject_unknown(payload, {"relation", "sql"}, "relation")
    return RelationInstructionDTO(
        relation=_text(payload, "relation"),
        sql=_text(payload, "sql"),
    )


def _decode_aggregate(payload: Mapping[str, Any]) -> AggregateInstructionDTO:
    _reject_unknown(payload, {"relation"}, "aggregate")
    return AggregateInstructionDTO(relation=_text(payload, "relation"))


def decode_core_instruction(
    value: InstructionDTO | CoreInstructionDTO | object,
) -> CoreInstructionDTO:
    """Read one typed core instruction from either its typed or stored form."""
    if isinstance(value, SourceRelationInstructionDTO | RelationInstructionDTO | AggregateInstructionDTO):
        return value
    instruction = decode_instruction(value)
    payload = instruction.payload
    if not isinstance(payload, Mapping):
        raise ValueError("core instruction payload must be an object")
    if instruction.kind == "source_relation":
        return _decode_source_relation(payload)
    if instruction.kind == "relation":
        return _decode_relation(payload)
    if instruction.kind == "aggregate":
        return _decode_aggregate(payload)
    raise ValueError(f"unknown core instruction kind {instruction.kind!r}")


__all__ = [
    "AggregateInstructionDTO",
    "CoreInstructionDTO",
    "DeclaredColumnDTO",
    "DeclaredPathDTO",
    "InstructionDTO",
    "RelationInstructionDTO",
    "SourceRelationInstructionDTO",
    "decode_core_instruction",
    "decode_instruction",
    "declared_column_type",
    "encode_declared_column",
    "encode_instruction",
    "instruction_document",
]
