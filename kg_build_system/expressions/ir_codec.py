"""Stable JSON codec for compilation expression IR."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from .._frozen_json import FrozenJson, FrozenObject, freeze_json
from ..types.ir_codec import decode_type_ir, encode_type_ir
from .ir import (
    ExpressionIR, FieldReferenceExpressionIR, LiteralExpressionIR,
    OperationExpressionIR, OperationParameterIR,
)


def _thaw(value: FrozenJson) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def encode_expression_ir(expression: ExpressionIR) -> dict[str, Any]:
    common = {"logical_type": encode_type_ir(expression.logical_type)}
    if isinstance(expression, LiteralExpressionIR):
        return {"kind": "literal", "value": _thaw(expression.value), **common}
    if isinstance(expression, FieldReferenceExpressionIR):
        return {
            "kind": "field", "source": expression.source,
            "path": list(expression.path),
            **common,
        }
    if isinstance(expression, OperationExpressionIR):
        return {
            "kind": "operation", "operator": expression.operator,
            "arguments": [encode_expression_ir(item) for item in expression.arguments],
            "parameters": {item.name: _thaw(item.value) for item in expression.parameters},
            **common,
        }
    raise TypeError(f"unsupported expression IR {expression!r}")


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"expression field {key!r} must be a non-empty string")
    return result


def _strings(value: Any, *, field: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"expression field {field!r} must be an array")
    result = tuple(value)
    if (not allow_empty and not result) or any(not isinstance(item, str) or not item for item in result):
        raise ValueError(f"expression field {field!r} must contain non-empty strings")
    return cast(tuple[str, ...], result)


def decode_expression_ir(value: Mapping[str, Any]) -> ExpressionIR:
    logical_type = decode_type_ir(_object(value.get("logical_type"), "logical_type"))
    common = {"logical_type": logical_type}
    kind = value.get("kind")
    if kind == "literal":
        return LiteralExpressionIR(value=freeze_json(value.get("value")), **common)
    if kind == "field":
        return FieldReferenceExpressionIR(
            source=_text(value, "source"), path=_strings(value.get("path"), field="path"),
            **common,
        )
    if kind == "operation":
        arguments_value = value.get("arguments")
        if not isinstance(arguments_value, Sequence) or isinstance(arguments_value, (str, bytes, bytearray)):
            raise ValueError("expression field 'arguments' must be an array")
        parameters = _object(value.get("parameters", {}), "parameters")
        return OperationExpressionIR(
            operator=_text(value, "operator"),
            arguments=tuple(decode_expression_ir(_object(item, "argument")) for item in arguments_value),
            parameters=tuple(OperationParameterIR(str(name), freeze_json(item)) for name, item in sorted(parameters.items())),
            **common,
        )
    raise ValueError(f"unknown expression kind {kind!r}")


__all__ = ["decode_expression_ir", "encode_expression_ir"]
