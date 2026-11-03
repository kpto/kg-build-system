"""Mechanisms behind operation specifications and the built-in operations."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from kg_build_system.kernel.model.internal.json import freeze_json
from kg_build_system.kernel.model.public.types import BOOL, INT, STR, ArrayType, LogicalType, NullableType, UnitType
from kg_build_system.kernel.service.internal.types import non_nullable
from ...model.internal.model import (
    ExpressionNode, FieldReferenceExpression, OperationExpression,
    OperationParameter, RowSemantics,
)
from .dto import expression_dto
from .dto_codec import expression_to_document
from .literals import literal
from .semantics import compose_row_semantics, row_effects
from .visitors import walk_expression

if TYPE_CHECKING:
    from ..internal.operations.spec import OperationSpec, RowEffectSpec

Arity = int | tuple[int, int | None]


def accepts_arity(spec: OperationSpec, count: int) -> bool:
    if isinstance(spec.arity, int):
        return count == spec.arity
    minimum, maximum = spec.arity
    return count >= minimum and (maximum is None or count <= maximum)


def arity_message(spec: OperationSpec) -> str:
    if isinstance(spec.arity, int):
        return f"{spec.name} requires {spec.arity} arguments"
    minimum, maximum = spec.arity
    if maximum is None:
        return f"{spec.name} requires at least {minimum} arguments"
    return f"{spec.name} requires between {minimum} and {maximum} arguments"


def argument_spec(spec: OperationSpec, index: int):
    if index < len(spec.arguments):
        return spec.arguments[index]
    if spec.repeat_last_argument and spec.arguments:
        return spec.arguments[-1]
    return None


def coerce_argument(
    spec: OperationSpec,
    value: Any,
    index: int,
    types: tuple[LogicalType, ...],
) -> ExpressionNode:
    if isinstance(value, ExpressionNode):
        return value
    model = getattr(value, "model", None)
    if isinstance(model, ExpressionNode):
        return model
    declared = argument_spec(spec, index)
    expected: LogicalType | None = None
    if declared is not None and declared.expected is not None:
        expected = (
            declared.expected(types)
            if callable(declared.expected)
            else declared.expected
        )
    return literal(value, logical_type=expected)


def resolve_parameters(
    spec: OperationSpec, values: Mapping[str, Any],
) -> dict[str, Any]:
    declared = {parameter.name: parameter for parameter in spec.parameters}
    unknown = set(values) - set(declared)
    if unknown:
        raise TypeError(
            f"{spec.name} received unknown parameters {sorted(unknown)}"
        )
    resolved: dict[str, Any] = {}
    for parameter in spec.parameters:
        if parameter.name in values:
            value = values[parameter.name]
        elif parameter.required:
            raise TypeError(
                f"{spec.name} requires parameter {parameter.name!r}"
            )
        else:
            value = parameter.default
        if parameter.accepts is not None and not parameter.accepts(value):
            raise ValueError(
                f"{spec.name} parameter {parameter.name!r} has invalid value {value!r}"
            )
        resolved[parameter.name] = value
    return resolved


def validate_types(
    spec: OperationSpec,
    nodes: tuple[ExpressionNode, ...],
    parameters: Mapping[str, Any],
) -> tuple[LogicalType, ...]:
    types = tuple(node.logical_type for node in nodes)
    for index, logical_type in enumerate(types):
        declared = argument_spec(spec, index)
        if (
            declared is not None
            and declared.accepts is not None
            and not declared.accepts(logical_type)
        ):
            raise TypeError(
                f"{spec.name} argument {index + 1} has logical type "
                f"{logical_type!r}, which is not a valid {declared.description}"
            )
    if spec.validate_arguments is not None:
        spec.validate_arguments(nodes, parameters)
    return types


def resolve_result(
    spec: OperationSpec,
    types: tuple[LogicalType, ...],
    parameters: Mapping[str, Any],
) -> LogicalType:
    if spec.result_type is None:
        raise TypeError(f"{spec.name} requires an explicit result type")
    if callable(spec.result_type):
        return spec.result_type(types, parameters)
    return spec.result_type


def resolve_row_effect_spec(
    row_effect: RowEffectSpec,
    nodes: tuple[ExpressionNode, ...],
    types: tuple[LogicalType, ...],
    parameters: Mapping[str, Any],
) -> RowSemantics:
    if row_effect.kind == "expand":
        if row_effect.scope is None:
            raise TypeError("expanding row effects require a scope resolver")
        scope = row_effect.scope(nodes, types, parameters)
        if not scope:
            raise ValueError("expanding row effects require a non-empty scope")
        return RowSemantics("expand", scope)
    return RowSemantics("filter")


def resolve_semantics(
    spec: OperationSpec,
    nodes: tuple[ExpressionNode, ...],
    types: tuple[LogicalType, ...],
    parameters: Mapping[str, Any],
) -> RowSemantics:
    from ..internal.operations.spec import RowEffectSpec

    if isinstance(spec.row_effect, RowEffectSpec):
        return resolve_row_effect_spec(spec.row_effect, nodes, types, parameters)
    if callable(spec.row_effect):
        return spec.row_effect(nodes, types, parameters)
    return spec.row_effect


def apply(
    spec: OperationSpec,
    *arguments: Any,
    result_type: LogicalType | None = None,
    **parameters: Any,
):
    if not accepts_arity(spec, len(arguments)):
        raise TypeError(arity_message(spec))
    resolved_parameters = resolve_parameters(spec, parameters)
    nodes: list[ExpressionNode] = []
    for index, value in enumerate(arguments):
        node = coerce_argument(
            spec, value, index, tuple(item.logical_type for item in nodes),
        )
        nodes.append(node)
    frozen_nodes = tuple(nodes)
    types = validate_types(spec, frozen_nodes, resolved_parameters)
    resolved_type = result_type or resolve_result(spec, types, resolved_parameters)
    local = resolve_semantics(spec, frozen_nodes, types, resolved_parameters)
    expression = OperationExpression(
        operator=spec.name,
        arguments=frozen_nodes,
        parameters=tuple(
            OperationParameter(name, freeze_json(value))
            for name, value in sorted(resolved_parameters.items())
        ),
        logical_type=resolved_type,
        row_semantics=compose_row_semantics(*frozen_nodes, local=local),
    )
    from .factory import wrap_expression

    return wrap_expression(expression)


def validate_numeric_operation(operator: str):
    def validate(
        arguments: Sequence[ExpressionNode], parameters: Mapping[str, Any],
    ) -> None:
        left, right = (argument.logical_type for argument in arguments)
        if left != right:
            raise TypeError(f"{operator} requires arguments of one numeric type")

    return validate


def nullable_str_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    return NullableType(STR) if any(isinstance(item, NullableType) for item in types) else STR


def validate_text_operation(operator: str):
    def validate(
        arguments: Sequence[ExpressionNode], parameters: Mapping[str, Any],
    ) -> None:
        if any(non_nullable(argument.logical_type) != STR for argument in arguments):
            raise TypeError(f"{operator} requires str arguments")

    return validate


def nullable_bool_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    return NullableType(BOOL) if any(isinstance(item, NullableType) for item in types) else BOOL


def positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def array_at_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    array = non_nullable(types[0])
    assert isinstance(array, ArrayType)
    return array.item if isinstance(array.item, NullableType) else NullableType(array.item)


def drop_null_items_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    source = types[0]
    array = non_nullable(source)
    assert isinstance(array, ArrayType)
    item = array.item.value if isinstance(array.item, NullableType) else array.item
    result = ArrayType(item)
    if isinstance(source, NullableType):
        result = NullableType(result)
    return result


def join_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    return NullableType(STR) if isinstance(types[0], NullableType) else STR


def coalesce_validate(
    arguments: Sequence[ExpressionNode], parameters: Mapping[str, Any],
) -> None:
    value = non_nullable(arguments[0].logical_type)
    for argument in arguments[1:]:
        if argument.logical_type != value:
            raise TypeError("coalesce arguments must share the value logical type")


def expand_scope(expression: ExpressionNode) -> tuple[str, ...]:
    if isinstance(expression, FieldReferenceExpression):
        return (expression.source, *expression.path)
    if isinstance(expression, OperationExpression):
        if (
            expression.operator == "struct_field"
            and len(expression.arguments) == 1
            and isinstance(expression.arguments[0], OperationExpression)
            and expression.arguments[0].operator == "expand"
        ):
            name = next(
                (item.value for item in expression.parameters if item.name == "name"),
                None,
            )
            parent_effects = row_effects(expression.arguments[0].row_semantics)
            if (
                isinstance(name, str)
                and name
                and parent_effects
                and parent_effects[-1].mode == "expand"
            ):
                return (*parent_effects[-1].scope, name)
        if expression.operator == "expand":
            effects = row_effects(expression.row_semantics)
            if effects and effects[-1].mode == "expand":
                return effects[-1].scope
    encoded = json.dumps(
        expression_to_document(expression_dto(expression)),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return ("expression", sha256(encoded).hexdigest())


def expand_scope_of(
    nodes: Sequence[ExpressionNode],
    types: tuple[LogicalType, ...],
    parameters: Mapping[str, Any],
) -> tuple[str, ...]:
    return expand_scope(nodes[0])


def expand_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    array = non_nullable(types[0])
    assert isinstance(array, ArrayType)
    return array.item


def transform_items_validate(
    arguments: Sequence[ExpressionNode], parameters: Mapping[str, Any],
) -> None:
    body = arguments[1]
    if any(row_effects(node.row_semantics) for node in walk_expression(body)):
        raise TypeError("transform_items selectors must not contain row effects")


def transform_items_result(
    types: tuple[LogicalType, ...], parameters: Mapping[str, Any],
) -> LogicalType:
    source, body = types
    array = non_nullable(source)
    assert isinstance(array, ArrayType)
    item = array.item
    if isinstance(item, NullableType) and not isinstance(body, NullableType):
        body = NullableType(body)
    result = ArrayType(body)
    if isinstance(source, NullableType):
        result = NullableType(result)
    return result


__all__ = [
    "accepts_arity", "apply", "arity_message", "argument_spec",
    "array_at_result", "coalesce_validate", "coerce_argument",
    "drop_null_items_result", "expand_result", "expand_scope", "expand_scope_of",
    "join_result", "nullable_bool_result", "nullable_str_result",
    "positive_integer", "resolve_parameters", "resolve_result",
    "resolve_row_effect_spec", "resolve_semantics", "transform_items_result",
    "transform_items_validate", "validate_numeric_operation",
    "validate_text_operation", "validate_types",
]
