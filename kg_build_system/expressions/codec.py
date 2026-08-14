"""Stable JSON-compatible codec for canonical expression trees."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..types import decode_type, encode_type
from .base import freeze_json
from .ir import (
    Expression, ExpressionNode, FieldReferenceExpression, FrozenJson, FrozenObject, LiteralExpression, OperationExpression,
    OperationParameter, RowEffect, RowSemantics, Traversal,
)


def _thaw(value: FrozenJson) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _encode_rows(rows: RowSemantics) -> dict[str, Any]:
    return {
        "effects": [
            {"mode": effect.mode, **({"scope": list(effect.scope)} if effect.scope else {})}
            for effect in rows.effects
        ]
    }


def encode_expression(expression: ExpressionNode) -> dict[str, Any]:
    common = {
        "logical_type": encode_type(expression.logical_type),
        "rows": _encode_rows(expression.row_semantics),
    }
    if isinstance(expression, LiteralExpression):
        return {"kind": "literal", "value": _thaw(expression.value), **common}
    if isinstance(expression, FieldReferenceExpression):
        return {
            "kind": "field",
            "source": expression.source,
            "path": list(expression.path),
            "traversals": [
                {"kind": traversal.kind, "path": list(traversal.path)}
                for traversal in expression.traversals
            ],
            **common,
        }
    if isinstance(expression, OperationExpression):
        return {
            "kind": "operation",
            "operator": expression.operator,
            "arguments": [encode_expression(argument) for argument in expression.arguments],
            "parameters": {parameter.name: _thaw(parameter.value) for parameter in expression.parameters},
            **common,
        }
    raise TypeError(f"unsupported canonical expression {expression!r}")


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    result = value.get(key)
    if not isinstance(result, Mapping):
        raise ValueError(f"expression field {key!r} must be an object")
    return result


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
    return result


def _rows(value: Mapping[str, Any]) -> RowSemantics:
    rows = _mapping(value, "rows")
    effects_value = rows.get("effects")
    if effects_value is not None:
        if not isinstance(effects_value, Sequence) or isinstance(effects_value, (str, bytes, bytearray)):
            raise ValueError("expression row effects must be an array")
        effects: list[RowEffect] = []
        for effect in effects_value:
            if not isinstance(effect, Mapping):
                raise ValueError("each expression row effect must be an object")
            mode = effect.get("mode")
            if mode not in {"expand", "filter"}:
                raise ValueError(f"unknown row-effect mode {mode!r}")
            effects.append(RowEffect(mode, _strings(effect.get("scope", ()), field="scope", allow_empty=True)))
        return RowSemantics.from_effects(tuple(effects))
    # Accept the earlier single-effect representation during the transition.
    mode = rows.get("mode")
    if mode not in {"preserve", "expand", "filter"}:
        raise ValueError(f"unknown row-semantics mode {mode!r}")
    return RowSemantics(mode, _strings(rows.get("scope", ()), field="scope", allow_empty=True))


def decode_expression(value: Mapping[str, Any]) -> Expression:
    logical_type = decode_type(_mapping(value, "logical_type"))
    rows = _rows(value)
    kind = value.get("kind")
    if kind == "literal":
        from .literals import literal
        result = literal(value.get("value"), logical_type=logical_type)
        return LiteralExpression(value=result.value, logical_type=logical_type, row_semantics=rows)
    if kind == "field":
        traversals_value = value.get("traversals", ())
        if not isinstance(traversals_value, Sequence) or isinstance(traversals_value, (str, bytes, bytearray)):
            raise ValueError("expression field 'traversals' must be an array")
        traversals = tuple(
            Traversal(_text(item, "kind"), _strings(item.get("path"), field="path"))  # type: ignore[arg-type]
            for item in traversals_value
            if isinstance(item, Mapping)
        )
        if len(traversals) != len(traversals_value):
            raise ValueError("each traversal must be an object")
        return FieldReferenceExpression(
            source=_text(value, "source"),
            path=_strings(value.get("path"), field="path"),
            traversals=traversals,
            logical_type=logical_type,
            row_semantics=rows,
        )
    if kind == "operation":
        arguments_value = value.get("arguments")
        if not isinstance(arguments_value, Sequence) or isinstance(arguments_value, (str, bytes, bytearray)):
            raise ValueError("expression field 'arguments' must be an array")
        if any(not isinstance(item, Mapping) for item in arguments_value):
            raise ValueError("each operation argument must be an object")
        parameters_value = value.get("parameters", {})
        if not isinstance(parameters_value, Mapping):
            raise ValueError("expression field 'parameters' must be an object")
        return OperationExpression(
            operator=_text(value, "operator"),
            arguments=tuple(decode_expression(item) for item in arguments_value),  # type: ignore[arg-type]
            parameters=tuple(OperationParameter(str(name), freeze_json(item)) for name, item in sorted(parameters_value.items())),
            logical_type=logical_type,
            row_semantics=rows,
        )
    raise ValueError(f"unknown expression kind {kind!r}")


__all__ = ["decode_expression", "encode_expression"]
