"""Canonical document codec for expression DTOs."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from kg_build_system.distribution.model.public.refs import (
    FieldRef, OperationRef, ref_from_document, ref_to_document,
)
from kg_build_system.kernel.model.internal.json import FrozenJson, FrozenObject, freeze_json
from kg_build_system.kernel.service.internal.types import type_from_document, type_to_document

from ...model.internal.dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, OperationParameterDTO, VariableExpressionDTO,
)


def thaw(value: FrozenJson) -> Any:
    if isinstance(value, FrozenObject):
        return {key: thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


def expression_to_document(expression: ExpressionDTO) -> dict[str, Any]:
    """Encode one expression DTO as its canonical JSON-compatible document."""
    common = {"logical_type": type_to_document(expression.logical_type)}
    if isinstance(expression, LiteralExpressionDTO):
        return {"kind": "literal", "value": thaw(expression.value), **common}
    if isinstance(expression, VariableExpressionDTO):
        return {"kind": "variable", "name": expression.name, **common}
    if isinstance(expression, FieldReferenceDTO):
        return {
            "kind": "field",
            "field": ref_to_document(expression.field),
            "path": list(expression.path),
            **common,
        }
    if isinstance(expression, OperationExpressionDTO):
        return {
            "kind": "operation",
            "operator": ref_to_document(expression.operator),
            "arguments": [
                expression_to_document(item) for item in expression.arguments
            ],
            "parameters": {
                item.name: thaw(item.value) for item in expression.parameters
            },
            **common,
        }
    raise TypeError(f"unsupported expression DTO {expression!r}")


def object_field(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def text_field(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"expression field {key!r} must be a non-empty string")
    return result


def string_sequence(
    value: Any, *, field: str, allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"expression field {field!r} must be an array")
    result = tuple(value)
    if (not allow_empty and not result) or any(
        not isinstance(item, str) or not item for item in result
    ):
        raise ValueError(f"expression field {field!r} must contain non-empty strings")
    return cast(tuple[str, ...], result)


def expression_from_document(value: Mapping[str, Any]) -> ExpressionDTO:
    """Decode one expression DTO from its canonical document."""
    logical_type = type_from_document(object_field(value.get("logical_type"), "logical_type"))
    common = {"logical_type": logical_type}
    kind = value.get("kind")
    if kind == "literal":
        return LiteralExpressionDTO(value=freeze_json(value.get("value")), **common)
    if kind == "variable":
        return VariableExpressionDTO(name=text_field(value, "name"), **common)
    if kind == "field":
        field = ref_from_document(value.get("field"))
        if not isinstance(field, FieldRef):
            raise ValueError("expression field 'field' must be a field reference")
        return FieldReferenceDTO(
            field=field,
            path=string_sequence(
                value.get("path", ()), field="path", allow_empty=True,
            ),
            **common,
        )
    if kind == "operation":
        arguments_value = value.get("arguments")
        if not isinstance(arguments_value, Sequence) or isinstance(
            arguments_value, (str, bytes, bytearray)
        ):
            raise ValueError("expression field 'arguments' must be an array")
        parameters = object_field(value.get("parameters", {}), "parameters")
        operator = ref_from_document(value.get("operator"))
        if not isinstance(operator, OperationRef):
            raise ValueError(
                "expression field 'operator' must be an operation reference"
            )
        return OperationExpressionDTO(
            operator=operator,
            arguments=tuple(
                expression_from_document(object_field(item, "argument"))
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
