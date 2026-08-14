"""Immutable version-2 blueprint declaration IR."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from ...expressions import ExpressionNode
from ...expressions.ir import FrozenJson
from ...types import LogicalType


@dataclass(frozen=True, slots=True)
class AnnotationDefinition:
    namespace: str
    annotation_id: str
    arguments: FrozenJson


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    name: str
    logical_type: LogicalType
    description: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class StructDefinition:
    symbol_id: str
    name: str
    fields: tuple[FieldDefinition, ...]
    description: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class TableDefinition:
    symbol_id: str
    name: str
    fields: tuple[FieldDefinition, ...]
    description: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class PropertyDefinition:
    name: str
    logical_type: LogicalType
    description: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    symbol_id: str
    name: str
    kind: Literal["node", "edge"]
    properties: tuple[PropertyDefinition, ...] = ()
    description: str | None = None
    source: str | None = None
    target: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionFieldDefinition:
    name: str
    expression: ExpressionNode
    description: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionDefinition:
    symbol_id: str
    name: str
    fields: tuple[ProjectionFieldDefinition, ...]
    description: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class NodeBindingDefinition:
    symbol_id: str
    component: str
    build_key: ExpressionNode
    properties: tuple[tuple[str, ExpressionNode], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()
    kind: Literal["node"] = "node"


@dataclass(frozen=True, slots=True)
class EdgeBindingDefinition:
    symbol_id: str
    component: str
    build_key: ExpressionNode
    source_build_key: ExpressionNode
    target_build_key: ExpressionNode
    properties: tuple[tuple[str, ExpressionNode], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()
    kind: Literal["edge"] = "edge"


BindingDefinition: TypeAlias = NodeBindingDefinition | EdgeBindingDefinition


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    symbol_id: str
    table: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None
    annotations: tuple[AnnotationDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class BlueprintModule:
    module_id: str
    module_import: str
    module_qualname: str
    configuration: FrozenJson | None = None


@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    """A complete declaration graph containing no Python class objects."""

    structs: tuple[StructDefinition, ...]
    tables: tuple[TableDefinition, ...]
    components: tuple[ComponentDefinition, ...]
    projections: tuple[ProjectionDefinition, ...]
    bindings: tuple[BindingDefinition, ...]
    sources: tuple[SourceDefinition, ...] = ()
    modules: tuple[BlueprintModule, ...] = ()
    schema_version: Literal[2] = 2

    def model_dump(self, *, mode: str = "python", **_: Any) -> dict[str, Any]:
        from .codec import encode_blueprint
        return encode_blueprint(self)

    def model_dump_json(self, *, indent: int | None = None, **_: Any) -> str:
        from .codec import blueprint_json
        return blueprint_json(self, indent=indent)

    @classmethod
    def model_validate(cls, value: Any) -> "BuildBlueprint":
        from collections.abc import Mapping
        from .codec import decode_blueprint
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("blueprints must be decoded from an object")
        return decode_blueprint(value)

    @classmethod
    def model_validate_json(cls, value: str | bytes | bytearray) -> "BuildBlueprint":
        from .codec import blueprint_from_json
        return blueprint_from_json(value)


__all__ = [
    "AnnotationDefinition", "BindingDefinition", "BlueprintModule", "BuildBlueprint",
    "ComponentDefinition", "EdgeBindingDefinition", "FieldDefinition", "NodeBindingDefinition",
    "ProjectionDefinition", "ProjectionFieldDefinition", "PropertyDefinition", "SourceDefinition",
    "StructDefinition", "TableDefinition",
]
