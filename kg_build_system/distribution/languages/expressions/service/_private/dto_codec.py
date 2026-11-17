"""Canonical document codec for expression DTOs."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from kg_build_system.distribution.model.public.refs import (
    FieldRef, OperationRef, RelationRef, ref_from_document, ref_to_document,
)
from kg_build_system.kernel.model.internal.json import FrozenJson, FrozenObject, freeze_json
from kg_build_system.kernel.service.internal.types import type_from_document, type_to_document

from ...model.internal.dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    LookupExpressionDTO, OperationExpressionDTO, OperationParameterDTO,
    VariableExpressionDTO,
)
from ...model.internal.dto.operation_dto import (
    ArgumentDTO, ExpressionsPartDTO, OperationDTO, ParameterDTO,
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
    if isinstance(expression, LookupExpressionDTO):
        return {
            "kind": "lookup",
            "relation": ref_to_document(expression.relation),
            "target_field": expression.target_field,
            "key": expression_to_document(expression.key),
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
        field = ref_from_document(string_sequence(value.get("field"), field="field"))
        if not isinstance(field, FieldRef):
            raise ValueError("expression field 'field' must be a field reference")
        return FieldReferenceDTO(
            field=field,
            path=string_sequence(
                value.get("path", ()), field="path", allow_empty=True,
            ),
            **common,
        )
    if kind == "lookup":
        relation = ref_from_document(
            string_sequence(value.get("relation"), field="relation")
        )
        if not isinstance(relation, RelationRef):
            raise ValueError(
                "expression field 'relation' must be a relation reference"
            )
        target_field = value.get("target_field", "")
        if not isinstance(target_field, str):
            raise ValueError(
                "expression field 'target_field' must be a string"
            )
        return LookupExpressionDTO(
            relation=relation,
            key=expression_from_document(object_field(value.get("key"), "key")),
            target_field=target_field,
            **common,
        )
    if kind == "operation":
        arguments_value = value.get("arguments")
        if not isinstance(arguments_value, Sequence) or isinstance(
            arguments_value, (str, bytes, bytearray)
        ):
            raise ValueError("expression field 'arguments' must be an array")
        parameters = object_field(value.get("parameters", {}), "parameters")
        operator = ref_from_document(
            string_sequence(value.get("operator"), field="operator")
        )
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


def _operation_to_document(operation: OperationDTO) -> dict[str, Any]:
    arity = (
        operation.arity
        if isinstance(operation.arity, int)
        else [operation.arity[0], operation.arity[1]]
    )
    return {
        "name": operation.name,
        "arity": arity,
        "arguments": [
            {
                "expected": (
                    None if argument.expected is None
                    else type_to_document(argument.expected)
                ),
                "description": argument.description,
            }
            for argument in operation.arguments
        ],
        "parameters": [
            {
                "name": parameter.name,
                "required": parameter.required,
                "default": (
                    None if parameter.default is None
                    else thaw(parameter.default)
                ),
            }
            for parameter in operation.parameters
        ],
        "result_type": (
            None if operation.result_type is None
            else type_to_document(operation.result_type)
        ),
        "row_effect": operation.row_effect,
    }


def _arity_from_document(value: Any) -> int | tuple[int, int | None]:
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 0:
            raise ValueError("operation arity must not be negative")
        return value
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("operation arity must be an integer or a pair")
    pair = tuple(value)
    if len(pair) != 2:
        raise ValueError("operation arity must be an integer or a pair")
    minimum, maximum = pair
    if (
        not isinstance(minimum, int) or isinstance(minimum, bool)
        or minimum < 0
    ):
        raise ValueError("operation minimum arity must be a non-negative integer")
    if maximum is not None and (
        not isinstance(maximum, int) or isinstance(maximum, bool)
    ):
        raise ValueError("operation maximum arity must be an integer or null")
    return (minimum, maximum)


def _argument_from_document(value: Mapping[str, Any]) -> ArgumentDTO:
    expected_document = value.get("expected")
    description = value.get("description")
    if not isinstance(description, str) or not description:
        raise ValueError("an operation argument requires a description")
    return ArgumentDTO(
        expected=(
            None if expected_document is None
            else type_from_document(
                object_field(expected_document, "operation argument expected"),
            )
        ),
        description=description,
    )


def _parameter_from_document(value: Mapping[str, Any]) -> ParameterDTO:
    required = value.get("required")
    if not isinstance(required, bool):
        raise ValueError("an operation parameter requires a required flag")
    default = value.get("default")
    return ParameterDTO(
        name=text_field(value, "name"),
        required=required,
        default=None if default is None else freeze_json(default),
    )


def _operation_from_document(value: Mapping[str, Any]) -> OperationDTO:
    row_effect = value.get("row_effect", "preserve")
    if row_effect not in {"preserve", "filter", "expand"}:
        raise ValueError(f"unknown row-effect kind {row_effect!r}")
    arguments_value = value.get("arguments", ())
    parameters_value = value.get("parameters", ())
    if not isinstance(arguments_value, Sequence) or isinstance(
        arguments_value, (str, bytes, bytearray)
    ):
        raise ValueError("operation field 'arguments' must be an array")
    if not isinstance(parameters_value, Sequence) or isinstance(
        parameters_value, (str, bytes, bytearray)
    ):
        raise ValueError("operation field 'parameters' must be an array")
    result_document = value.get("result_type")
    return OperationDTO(
        name=text_field(value, "name"),
        arity=_arity_from_document(value.get("arity")),
        arguments=tuple(
            _argument_from_document(object_field(item, "operation argument"))
            for item in arguments_value
        ),
        parameters=tuple(
            _parameter_from_document(object_field(item, "operation parameter"))
            for item in parameters_value
        ),
        result_type=(
            None if result_document is None
            else type_from_document(
                object_field(result_document, "operation result type"),
            )
        ),
        row_effect=cast(Any, row_effect),
    )


def expressions_part_to_document(part: ExpressionsPartDTO) -> dict[str, Any]:
    """Encode the expressions part as its canonical document."""
    return {
        "operations": [
            _operation_to_document(operation) for operation in part.operations
        ],
    }


def expressions_part_from_document(value: Mapping[str, Any]) -> ExpressionsPartDTO:
    """Decode the expressions part from its canonical document."""
    if not isinstance(value, Mapping):
        raise ValueError("the expressions part must be an object")
    operations = value.get("operations", ())
    if not isinstance(operations, Sequence) or isinstance(
        operations, (str, bytes, bytearray)
    ):
        raise ValueError("expressions part field 'operations' must be an array")
    return ExpressionsPartDTO(
        operations=tuple(
            _operation_from_document(object_field(item, "operation"))
            for item in operations
        ),
    )


__all__ = [
    "expression_from_document", "expression_to_document",
    "expressions_part_from_document", "expressions_part_to_document",
]
