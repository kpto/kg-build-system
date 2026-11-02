"""Serializable execution instructions owned by the core workflow module.

The ``action`` discriminator and the payload fields keep the shape the workflow
contract already carries. A module executor never sees the blueprint, so every
fact a core step needs at execution time travels in its own instruction.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Literal, TypeAlias

from ...._frozen_json import FrozenJson, freeze_json, thaw_json
from ....types.internal import decode_type_ir, encode_type_ir
from ....types.internal.ir import LogicalTypeIR


@dataclass(frozen=True, slots=True)
class CoreInstructionIR:
    """Marker base for the core step instruction kinds."""


@dataclass(frozen=True, slots=True)
class DeclaredPathIR:
    """One declared member path, in both forms the source step needs."""

    schema_path: str
    logical_path: str

    def __post_init__(self) -> None:
        if not self.schema_path:
            raise ValueError("declared schema paths must be non-empty")
        if not self.logical_path:
            raise ValueError("declared logical paths must be non-empty")


@dataclass(frozen=True, slots=True)
class DeclaredColumnIR:
    """One declared top-level field, with the type it is declared to hold."""

    name: str
    logical_type: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("declared columns require a non-empty name")
        if not isinstance(self.logical_type, Mapping):
            raise ValueError("declared column types must be objects")
        decode_type_ir(self.logical_type)
        object.__setattr__(self, "logical_type", dict(self.logical_type))


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceRelationInstructionIR(CoreInstructionIR):
    """Read one physical source and expose its widened, typed relation."""

    action: Literal["source_relation"] = "source_relation"
    relation: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    declaration: str = ""
    declared_columns: tuple[DeclaredColumnIR, ...] = ()
    declared_paths: tuple[DeclaredPathIR, ...] = ()

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


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationInstructionIR(CoreInstructionIR):
    """Define one named relation from SQL the module already lowered."""

    action: Literal["relation"] = "relation"
    relation: str
    sql: str

    def __post_init__(self) -> None:
        if not self.relation:
            raise ValueError("relation instructions require a non-empty relation")
        if not self.sql:
            raise ValueError("relation instructions require non-empty SQL")


@dataclass(frozen=True, slots=True, kw_only=True)
class AggregateInstructionIR(CoreInstructionIR):
    """Union every binding relation of one bound component into graph records."""

    action: Literal["aggregate"] = "aggregate"
    relation: str

    def __post_init__(self) -> None:
        if not self.relation:
            raise ValueError("aggregate instructions require a non-empty relation")


CoreStepInstructionIR: TypeAlias = (
    SourceRelationInstructionIR | RelationInstructionIR | AggregateInstructionIR
)


def declared_column_type(column: DeclaredColumnIR) -> LogicalTypeIR:
    """The declared logical type, as the compilation IR states it."""
    return decode_type_ir(column.logical_type)


def encode_declared_column(name: str, logical_type: LogicalTypeIR) -> DeclaredColumnIR:
    """One declared column, carrying the logical type in its JSON form."""
    return DeclaredColumnIR(name=name, logical_type=encode_type_ir(logical_type))


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"core instruction field {key!r} must be a non-empty string")
    return item


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str) or not item:
        raise ValueError(f"core instruction field {key!r} must be a non-empty string")
    return item


def _sequence(value: Any, key: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    raise ValueError(f"core instruction field {key!r} must be a sequence")


def _mapping(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"core instruction field {key!r} must be an object")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], action: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(
            f"unknown field(s) {', '.join(sorted(map(repr, unknown)))} "
            f"in {action} instruction"
        )


def _declared_path(value: Any) -> DeclaredPathIR:
    if isinstance(value, DeclaredPathIR):
        return value
    data = _mapping(value, "declared_paths")
    _reject_unknown(data, {"schema_path", "logical_path"}, "source_relation")
    return DeclaredPathIR(
        schema_path=_text(data, "schema_path"),
        logical_path=_text(data, "logical_path"),
    )


def _declared_column(value: Any) -> DeclaredColumnIR:
    if isinstance(value, DeclaredColumnIR):
        return value
    data = _mapping(value, "declared_columns")
    _reject_unknown(data, {"name", "logical_type"}, "source_relation")
    return DeclaredColumnIR(
        name=_text(data, "name"),
        logical_type=dict(_mapping(data.get("logical_type"), "logical_type")),
    )


def _decode_source_relation(data: Mapping[str, Any]) -> SourceRelationInstructionIR:
    _reject_unknown(
        data,
        {
            "action", "relation", "location", "format", "credential_reference",
            "declaration", "declared_columns", "declared_paths",
        },
        "source_relation",
    )
    format_value = data.get("format")
    if format_value not in {"csv", "json", "parquet"}:
        raise ValueError(f"unknown source format {format_value!r}")
    declaration = data.get("declaration", "")
    if not isinstance(declaration, str):
        raise ValueError("core instruction field 'declaration' must be a string")
    return SourceRelationInstructionIR(
        relation=_text(data, "relation"),
        location=_text(data, "location"),
        format=format_value,
        credential_reference=_optional_text(data, "credential_reference"),
        declaration=declaration,
        declared_columns=tuple(
            _declared_column(item)
            for item in _sequence(data.get("declared_columns"), "declared_columns")
        ),
        declared_paths=tuple(
            _declared_path(item)
            for item in _sequence(data.get("declared_paths"), "declared_paths")
        ),
    )


def _decode_relation(data: Mapping[str, Any]) -> RelationInstructionIR:
    _reject_unknown(data, {"action", "relation", "sql"}, "relation")
    return RelationInstructionIR(
        relation=_text(data, "relation"),
        sql=_text(data, "sql"),
    )


def _decode_aggregate(data: Mapping[str, Any]) -> AggregateInstructionIR:
    _reject_unknown(data, {"action", "relation"}, "aggregate")
    return AggregateInstructionIR(relation=_text(data, "relation"))


_DECODERS = {
    "source_relation": _decode_source_relation,
    "relation": _decode_relation,
    "aggregate": _decode_aggregate,
}


def decode_core_instruction(value: object) -> CoreStepInstructionIR:
    """One instruction from its frozen contract form."""
    data = thaw_json(value)  # type: ignore[arg-type]
    if not isinstance(data, Mapping):
        raise ValueError("core workflow steps require an object payload")
    action = data.get("action")
    decoder = _DECODERS.get(action) if isinstance(action, str) else None
    if decoder is None:
        raise ValueError(f"unknown core instruction action {action!r}")
    return decoder(data)


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


def encode_core_instruction(value: CoreStepInstructionIR) -> FrozenJson:
    """The frozen contract form of one instruction."""
    return freeze_json(_plain(value))


__all__ = [
    "AggregateInstructionIR",
    "CoreInstructionIR",
    "CoreStepInstructionIR",
    "DeclaredColumnIR",
    "DeclaredPathIR",
    "RelationInstructionIR",
    "SourceRelationInstructionIR",
    "decode_core_instruction",
    "declared_column_type",
    "encode_core_instruction",
    "encode_declared_column",
]
