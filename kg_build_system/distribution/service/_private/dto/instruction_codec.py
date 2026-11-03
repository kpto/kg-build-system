"""Codec for the distribution instruction DTOs.

The DTOs themselves live in
:mod:`kg_build_system.distribution.model.internal.dto`; this module is the
mechanism that reads and writes their stored form.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any

from pydantic import JsonValue

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from kg_build_system.kernel.service.internal.types import type_from_document, type_to_document
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO
from ....model.internal.dto.instruction_dto import (
    AggregateInstructionDTO,
    CoreInstructionDTO,
    DeclaredColumnDTO,
    DeclaredPathDTO,
    InstructionDTO,
    RelationInstructionDTO,
    SourceRelationInstructionDTO,
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
    if isinstance(
        value,
        (SourceRelationInstructionDTO, RelationInstructionDTO, AggregateInstructionDTO),
    ):
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
    "decode_core_instruction",
    "decode_instruction",
    "declared_column_type",
    "encode_declared_column",
    "encode_instruction",
    "instruction_document",
]
