"""Stable JSON encoding and decoding for build blueprints."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar, cast

from ..expressions.dto_codec import decode_expression_dto, encode_expression_dto
from ..expressions.base import freeze_json
from .._frozen_json import FrozenJson, FrozenObject
from ..types.dto_codec import decode_type_dto, encode_type_dto
from ..annotations.dto import AnnotationDTO as AnnotationDefinition
from ..binding.dto import (
    EdgeBindingDTO as EdgeBindingDefinition,
    NodeBindingDTO as NodeBindingDefinition,
)
from ..table.dto import (
    FieldDTO as FieldDefinition,
    ProjectionDTO as ProjectionDefinition,
    ProjectionFieldDTO as ProjectionFieldDefinition,
    SourceDTO as SourceDefinition,
    StructDTO as StructDefinition,
    TableDTO as TableDefinition,
)
from ..topology.dto import ComponentDTO as ComponentDefinition, PropertyDTO as PropertyDefinition
from ..workflow.dto import BlueprintModuleDTO as BlueprintModule
from .blueprint import BLUEPRINT_SCHEMA_VERSION, BuildBlueprint
from .validation import validate_blueprint

T = TypeVar("T")


def _thaw(value: FrozenJson) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _encode_annotation(value: AnnotationDefinition) -> dict[str, Any]:
    return {
        "namespace": value.namespace,
        "annotation_id": value.annotation_id,
        "arguments": _thaw(value.arguments),
    }


def _encode_typed_declaration(
    value: FieldDefinition | PropertyDefinition,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "logical_type": encode_type_dto(value.logical_type),
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _encode_data_declaration(
    value: StructDefinition | TableDefinition,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "name": value.name,
        "fields": [_encode_typed_declaration(field) for field in value.fields],
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _encode_component(value: ComponentDefinition) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "name": value.name,
        "kind": value.kind,
        "properties": [
            _encode_typed_declaration(prop) for prop in value.properties
        ],
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    if value.kind == "edge":
        result["source"] = value.source
        result["target"] = value.target
    return result


def _encode_projection(value: ProjectionDefinition) -> dict[str, Any]:
    fields = []
    for field in value.fields:
        encoded: dict[str, Any] = {
            "name": field.name,
            "expression": encode_expression_dto(field.expression),
            "annotations": [
                _encode_annotation(item) for item in field.annotations
            ],
        }
        if field.description is not None:
            encoded["description"] = field.description
        fields.append(encoded)

    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "name": value.name,
        "fields": fields,
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _encode_binding(
    value: NodeBindingDefinition | EdgeBindingDefinition,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": value.kind,
        "symbol_id": value.symbol_id,
        "component": value.component,
        "build_key": encode_expression_dto(value.build_key),
        "properties": {
            name: encode_expression_dto(expression)
            for name, expression in value.properties
        },
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.debug_name is not None:
        result["debug_name"] = value.debug_name
    if isinstance(value, EdgeBindingDefinition):
        result["source_build_key"] = encode_expression_dto(value.source_build_key)
        result["target_build_key"] = encode_expression_dto(value.target_build_key)
    return result


def _encode_source(value: SourceDefinition) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "table": value.table,
        "location": value.location,
        "format": value.format,
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.credential_reference is not None:
        result["credential_reference"] = value.credential_reference
    if value.version is not None:
        result["version"] = value.version
    return result


def _encode_module(value: BlueprintModule) -> dict[str, Any]:
    return {
        "module_id": value.module_id,
        "module_import": value.module_import,
        "module_qualname": value.module_qualname,
        "configuration": (
            None if value.configuration is None else _thaw(value.configuration)
        ),
    }


def encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    """Encode a blueprint into its canonical JSON-compatible representation."""
    return {
        "schema_version": BLUEPRINT_SCHEMA_VERSION,
        "structs": [_encode_data_declaration(item) for item in value.structs],
        "tables": [_encode_data_declaration(item) for item in value.tables],
        "components": [_encode_component(item) for item in value.components],
        "projections": [_encode_projection(item) for item in value.projections],
        "bindings": [_encode_binding(item) for item in value.bindings],
        "sources": [_encode_source(item) for item in value.sources],
        "modules": [_encode_module(item) for item in value.modules],
    }


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{context} must be an array")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is not None and (not isinstance(result, str) or not result):
        raise ValueError(f"{key!r} must be null or a non-empty string")
    return result


def _items(
    value: Mapping[str, Any],
    key: str,
    decoder: Callable[[Mapping[str, Any]], T],
) -> tuple[T, ...]:
    return tuple(
        decoder(_object(item, key)) for item in _array(value.get(key, ()), key)
    )


def _decode_annotation(value: Mapping[str, Any]) -> AnnotationDefinition:
    return AnnotationDefinition(
        namespace=_text(value, "namespace"),
        annotation_id=_text(value, "annotation_id"),
        arguments=freeze_json(value.get("arguments")),
    )


def _decode_field(value: Mapping[str, Any]) -> FieldDefinition:
    return FieldDefinition(
        name=_text(value, "name"),
        logical_type=decode_type_dto(_object(value.get("logical_type"), "logical_type")),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_property(value: Mapping[str, Any]) -> PropertyDefinition:
    return PropertyDefinition(
        name=_text(value, "name"),
        logical_type=decode_type_dto(_object(value.get("logical_type"), "logical_type")),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_struct(value: Mapping[str, Any]) -> StructDefinition:
    return StructDefinition(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        fields=_items(value, "fields", _decode_field),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_table(value: Mapping[str, Any]) -> TableDefinition:
    return TableDefinition(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        fields=_items(value, "fields", _decode_field),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_component(value: Mapping[str, Any]) -> ComponentDefinition:
    kind = value.get("kind")
    if kind not in {"node", "edge"}:
        raise ValueError(f"unknown component kind {kind!r}")
    return ComponentDefinition(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        kind=cast(Any, kind),
        properties=_items(value, "properties", _decode_property),
        description=_optional_text(value, "description"),
        source=_optional_text(value, "source"),
        target=_optional_text(value, "target"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_projection_field(
    value: Mapping[str, Any],
) -> ProjectionFieldDefinition:
    return ProjectionFieldDefinition(
        name=_text(value, "name"),
        expression=decode_expression_dto(_object(value.get("expression"), "expression")),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_projection(value: Mapping[str, Any]) -> ProjectionDefinition:
    return ProjectionDefinition(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        fields=_items(value, "fields", _decode_projection_field),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_properties(
    value: Mapping[str, Any],
) -> tuple[tuple[str, Any], ...]:
    properties = _object(value.get("properties", {}), "properties")
    return tuple(
        sorted(
            (
                str(name),
                decode_expression_dto(_object(expression, "property expression")),
            )
            for name, expression in properties.items()
        )
    )


def _decode_binding(
    value: Mapping[str, Any],
) -> NodeBindingDefinition | EdgeBindingDefinition:
    common = {
        "symbol_id": _text(value, "symbol_id"),
        "component": _text(value, "component"),
        "build_key": decode_expression_dto(_object(value.get("build_key"), "build_key")),
        "properties": _decode_properties(value),
        "debug_name": _optional_text(value, "debug_name"),
        "annotations": _items(value, "annotations", _decode_annotation),
    }
    kind = value.get("kind")
    if kind == "node":
        return NodeBindingDefinition(**common)
    if kind == "edge":
        return EdgeBindingDefinition(
            **common,
            source_build_key=decode_expression_dto(
                _object(value.get("source_build_key"), "source_build_key")
            ),
            target_build_key=decode_expression_dto(
                _object(value.get("target_build_key"), "target_build_key")
            ),
        )
    raise ValueError(f"unknown binding kind {kind!r}")


def _decode_source(value: Mapping[str, Any]) -> SourceDefinition:
    source_format = value.get("format")
    if source_format not in {"csv", "json", "parquet"}:
        raise ValueError(f"unknown source format {source_format!r}")
    return SourceDefinition(
        symbol_id=_text(value, "symbol_id"),
        table=_text(value, "table"),
        location=_text(value, "location"),
        format=cast(Any, source_format),
        credential_reference=_optional_text(value, "credential_reference"),
        version=_optional_text(value, "version"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_module(value: Mapping[str, Any]) -> BlueprintModule:
    configuration = value.get("configuration")
    return BlueprintModule(
        module_id=_text(value, "module_id"),
        module_import=_text(value, "module_import"),
        module_qualname=_text(value, "module_qualname"),
        configuration=(
            None if configuration is None else freeze_json(configuration)
        ),
    )


def decode_blueprint(value: Mapping[str, Any]) -> BuildBlueprint:
    """Decode and validate a blueprint from a JSON-compatible object."""
    version = value.get("schema_version")
    if version != BLUEPRINT_SCHEMA_VERSION:
        raise ValueError(f"unsupported blueprint schema version {version!r}")

    result = BuildBlueprint(
        structs=_items(value, "structs", _decode_struct),
        tables=_items(value, "tables", _decode_table),
        components=_items(value, "components", _decode_component),
        projections=_items(value, "projections", _decode_projection),
        bindings=_items(value, "bindings", _decode_binding),
        sources=_items(value, "sources", _decode_source),
        modules=_items(value, "modules", _decode_module),
    )
    validate_blueprint(result)
    return result


def blueprint_json(value: BuildBlueprint, *, indent: int | None = None) -> str:
    validate_blueprint(value)
    return json.dumps(
        encode_blueprint(value),
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )


def blueprint_from_json(value: str | bytes | bytearray) -> BuildBlueprint:
    return decode_blueprint(_object(json.loads(value), "blueprint"))


__all__ = [
    "blueprint_from_json",
    "blueprint_json",
    "decode_blueprint",
    "encode_blueprint",
]
