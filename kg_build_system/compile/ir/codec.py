"""Canonical JSON codec for version-2 build blueprints."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from ...expressions import decode_expression, encode_expression
from ...expressions.base import freeze_json
from ...expressions.ir import FrozenObject
from ...types import decode_type, encode_type
from .models import *
from .validation import validate_blueprint


def _thaw(value):
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _annotation(value):
    return {"namespace": value.namespace, "annotation_id": value.annotation_id, "arguments": _thaw(value.arguments)}


def _typed(value):
    return {"name": value.name, "logical_type": encode_type(value.logical_type), **({"description": value.description} if value.description is not None else {}), "annotations": [_annotation(item) for item in value.annotations]}


def encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    def data(item):
        return {"symbol_id": item.symbol_id, "name": item.name, **({"description": item.description} if item.description is not None else {}), "fields": [_typed(field) for field in item.fields], "annotations": [_annotation(a) for a in item.annotations]}
    def component(item):
        return {"symbol_id": item.symbol_id, "name": item.name, "kind": item.kind, **({"description": item.description} if item.description is not None else {}), **({"source": item.source, "target": item.target} if item.kind == "edge" else {}), "properties": [_typed(prop) for prop in item.properties], "annotations": [_annotation(a) for a in item.annotations]}
    def projection(item):
        return {"symbol_id": item.symbol_id, "name": item.name, **({"description": item.description} if item.description is not None else {}), "fields": [{"name": field.name, "expression": encode_expression(field.expression), **({"description": field.description} if field.description is not None else {}), "annotations": [_annotation(a) for a in field.annotations]} for field in item.fields], "annotations": [_annotation(a) for a in item.annotations]}
    def binding(item):
        result = {"kind": item.kind, "symbol_id": item.symbol_id, "component": item.component, **({"debug_name": item.debug_name} if item.debug_name is not None else {}), "build_key": encode_expression(item.build_key), "properties": {name: encode_expression(expression) for name, expression in item.properties}, "annotations": [_annotation(a) for a in item.annotations]}
        if isinstance(item, EdgeBindingDefinition):
            result.update(source_build_key=encode_expression(item.source_build_key), target_build_key=encode_expression(item.target_build_key))
        return result
    return {
        "schema_version": 2,
        "structs": [data(item) for item in value.structs], "tables": [data(item) for item in value.tables],
        "components": [component(item) for item in value.components], "projections": [projection(item) for item in value.projections],
        "bindings": [binding(item) for item in value.bindings],
        "sources": [{"symbol_id": item.symbol_id, "table": item.table, "location": item.location, "format": item.format, **({"credential_reference": item.credential_reference} if item.credential_reference else {}), **({"version": item.version} if item.version else {}), "annotations": [_annotation(a) for a in item.annotations]} for item in value.sources],
        "modules": [{"module_id": item.module_id, "module_import": item.module_import, "module_qualname": item.module_qualname, "configuration": None if item.configuration is None else _thaw(item.configuration)} for item in value.modules],
    }


def _obj(value, context):
    if not isinstance(value, Mapping): raise ValueError(f"{context} must be an object")
    return value
def _arr(value, context):
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)): raise ValueError(f"{context} must be an array")
    return value
def _text(value, key):
    result = value.get(key)
    if not isinstance(result, str) or not result: raise ValueError(f"{key!r} must be a non-empty string")
    return result
def _optional(value, key):
    result = value.get(key)
    if result is not None and (not isinstance(result, str) or not result): raise ValueError(f"{key!r} must be null or a non-empty string")
    return result
def _items(value, key, decoder):
    return tuple(decoder(_obj(item, key)) for item in _arr(value.get(key, ()), key))
def _decode_annotation(value):
    return AnnotationDefinition(_text(value, "namespace"), _text(value, "annotation_id"), freeze_json(value.get("arguments")))
def _decode_typed(value):
    return FieldDefinition(_text(value, "name"), decode_type(_obj(value.get("logical_type"), "logical_type")), _optional(value, "description"), _items(value, "annotations", _decode_annotation))
def _decode_property(value):
    return PropertyDefinition(_text(value, "name"), decode_type(_obj(value.get("logical_type"), "logical_type")), _optional(value, "description"), _items(value, "annotations", _decode_annotation))


def decode_blueprint(value: Mapping[str, Any]) -> BuildBlueprint:
    if value.get("schema_version") != 2: raise ValueError(f"unsupported blueprint schema version {value.get('schema_version')!r}")
    def struct(item): return StructDefinition(_text(item, "symbol_id"), _text(item, "name"), _items(item, "fields", _decode_typed), _optional(item, "description"), _items(item, "annotations", _decode_annotation))
    def table(item): return TableDefinition(_text(item, "symbol_id"), _text(item, "name"), _items(item, "fields", _decode_typed), _optional(item, "description"), _items(item, "annotations", _decode_annotation))
    def component(item):
        kind = item.get("kind")
        if kind not in {"node", "edge"}: raise ValueError(f"unknown component kind {kind!r}")
        return ComponentDefinition(_text(item, "symbol_id"), _text(item, "name"), kind, _items(item, "properties", _decode_property), _optional(item, "description"), _optional(item, "source"), _optional(item, "target"), _items(item, "annotations", _decode_annotation))
    def projection(item):
        def field(raw): return ProjectionFieldDefinition(_text(raw, "name"), decode_expression(_obj(raw.get("expression"), "expression")), _optional(raw, "description"), _items(raw, "annotations", _decode_annotation))
        return ProjectionDefinition(_text(item, "symbol_id"), _text(item, "name"), _items(item, "fields", field), _optional(item, "description"), _items(item, "annotations", _decode_annotation))
    def binding(item):
        properties_obj = _obj(item.get("properties", {}), "properties")
        properties = tuple(sorted((str(name), decode_expression(_obj(expression, "property expression"))) for name, expression in properties_obj.items()))
        common = (_text(item, "symbol_id"), _text(item, "component"), decode_expression(_obj(item.get("build_key"), "build_key")))
        rest = (properties, _optional(item, "debug_name"), _items(item, "annotations", _decode_annotation))
        if item.get("kind") == "node": return NodeBindingDefinition(*common, *rest)
        if item.get("kind") == "edge": return EdgeBindingDefinition(*common, decode_expression(_obj(item.get("source_build_key"), "source_build_key")), decode_expression(_obj(item.get("target_build_key"), "target_build_key")), *rest)
        raise ValueError(f"unknown binding kind {item.get('kind')!r}")
    def source(item):
        format_value = item.get("format")
        if format_value not in {"csv", "json", "parquet"}: raise ValueError(f"unknown source format {format_value!r}")
        return SourceDefinition(_text(item, "symbol_id"), _text(item, "table"), _text(item, "location"), format_value, _optional(item, "credential_reference"), _optional(item, "version"), _items(item, "annotations", _decode_annotation))
    def module(item):
        config = item.get("configuration")
        return BlueprintModule(_text(item, "module_id"), _text(item, "module_import"), _text(item, "module_qualname"), None if config is None else freeze_json(config))
    result = BuildBlueprint(_items(value, "structs", struct), _items(value, "tables", table), _items(value, "components", component), _items(value, "projections", projection), _items(value, "bindings", binding), _items(value, "sources", source), _items(value, "modules", module))
    validate_blueprint(result)
    return result


def blueprint_json(value: BuildBlueprint, *, indent: int | None = None) -> str:
    validate_blueprint(value)
    return json.dumps(encode_blueprint(value), sort_keys=True, indent=indent, separators=(",", ":") if indent is None else None)
def blueprint_from_json(value: str | bytes | bytearray) -> BuildBlueprint:
    return decode_blueprint(_obj(json.loads(value), "blueprint"))


__all__ = ["blueprint_from_json", "blueprint_json", "decode_blueprint", "encode_blueprint"]
