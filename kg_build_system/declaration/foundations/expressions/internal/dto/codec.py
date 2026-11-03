"""Canonical document codec for expression DTOs."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from kg_build_system.kernel.internal.json import FrozenJson, FrozenObject, freeze_json
from kg_build_system.kernel.internal.types import type_from_document, type_to_document

from .blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, OperationParameterDTO, VariableExpressionDTO,
)


def _thaw(value: FrozenJson) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def expression_to_document(expression: ExpressionDTO) -> dict[str, Any]:
    """Encode one expression DTO as its canonical JSON-compatible document.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.internal import (
            LiteralExpressionDTO, expression_to_document,
        )
        from kg_build_system.kernel.internal.types.dto import UnitTypeDTO

        node = LiteralExpressionDTO(logical_type=UnitTypeDTO("int"), value=1)
        assert expression_to_document(node)["kind"] == "literal"
        ```
    """
    common = {"logical_type": type_to_document(expression.logical_type)}
    if isinstance(expression, LiteralExpressionDTO):
        return {"kind": "literal", "value": _thaw(expression.value), **common}
    if isinstance(expression, VariableExpressionDTO):
        return {"kind": "variable", "name": expression.name, **common}
    if isinstance(expression, FieldReferenceDTO):
        return {
            "kind": "field",
            "source": expression.source,
            "path": list(expression.path),
            **common,
        }
    if isinstance(expression, OperationExpressionDTO):
        return {
            "kind": "operation",
            "operator": expression.operator,
            "arguments": [
                expression_to_document(item) for item in expression.arguments
            ],
            "parameters": {
                item.name: _thaw(item.value) for item in expression.parameters
            },
            **common,
        }
    raise TypeError(f"unsupported expression DTO {expression!r}")


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
    if (not allow_empty and not result) or any(
        not isinstance(item, str) or not item for item in result
    ):
        raise ValueError(f"expression field {field!r} must contain non-empty strings")
    return cast(tuple[str, ...], result)


def expression_from_document(value: Mapping[str, Any]) -> ExpressionDTO:
    """Decode one expression DTO from its canonical document.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.internal import (
            expression_from_document,
        )

        node = expression_from_document({
            "kind": "literal",
            "value": 1,
            "logical_type": {"kind": "unit", "name": "int"},
        })
        assert node.logical_type.name == "int"
        ```
    """
    logical_type = type_from_document(_object(value.get("logical_type"), "logical_type"))
    common = {"logical_type": logical_type}
    kind = value.get("kind")
    if kind == "literal":
        return LiteralExpressionDTO(value=freeze_json(value.get("value")), **common)
    if kind == "variable":
        return VariableExpressionDTO(name=_text(value, "name"), **common)
    if kind == "field":
        return FieldReferenceDTO(
            source=_text(value, "source"),
            path=_strings(value.get("path"), field="path"),
            **common,
        )
    if kind == "operation":
        arguments_value = value.get("arguments")
        if not isinstance(arguments_value, Sequence) or isinstance(
            arguments_value, (str, bytes, bytearray)
        ):
            raise ValueError("expression field 'arguments' must be an array")
        parameters = _object(value.get("parameters", {}), "parameters")
        return OperationExpressionDTO(
            operator=_text(value, "operator"),
            arguments=tuple(
                expression_from_document(_object(item, "argument"))
                for item in arguments_value
            ),
            parameters=tuple(
                OperationParameterDTO(str(name), freeze_json(item))
                for name, item in sorted(parameters.items())
            ),
            **common,
        )
    raise ValueError(f"unknown expression kind {kind!r}")


__all__ = ["expression_from_document", "expression_to_document"]
