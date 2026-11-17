"""Render expression DTOs back to inline authoring source."""
from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from kg_build_system.kernel.model.internal.types.dto import ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO, UnitTypeDTO

from kg_build_system.kernel import SourceFragment
from ...model.internal.dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    LookupExpressionDTO, OperationExpressionDTO, VariableExpressionDTO,
)
from ...model.internal.dto.operation_dto import RowEffectKind
from .dto_codec import expression_to_document

UNIT_NAMES = {
    "bool": "BOOL",
    "int": "INT",
    "float": "FLOAT",
    "str": "STR",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
    "uuid": "UUID",
}


def render_type(logical_type: LogicalTypeDTO) -> str:
    if isinstance(logical_type, UnitTypeDTO):
        return UNIT_NAMES[logical_type.name]
    if isinstance(logical_type, CustomTypeDTO):
        return f"CustomType({logical_type.module!r}, {logical_type.qualname!r})"
    if isinstance(logical_type, StructTypeDTO):
        return f"StructType({logical_type.module!r}, {logical_type.qualname!r})"
    if isinstance(logical_type, ArrayTypeDTO):
        return f"ArrayType({render_type(logical_type.item)})"
    if isinstance(logical_type, NullableTypeDTO):
        return f"NullableType({render_type(logical_type.value)})"
    raise TypeError(f"unsupported logical type {logical_type!r}")


def render_value(value: Any) -> str:
    if isinstance(value, FrozenObject):
        items = ", ".join(
            f"{key!r}: {render_value(thaw_json(item))}"
            for key, item in value.items
        )
        return "{" + items + "}"
    if isinstance(value, tuple):
        return "[" + ", ".join(render_value(item) for item in value) + "]"
    return repr(value)


def _literal_source(expression: LiteralExpressionDTO) -> str:
    return (
        "value_expression("
        f"{render_value(expression.value)}, "
        f"logical_type={render_type(expression.logical_type)})"
    )


def _expand_scope(expression: ExpressionDTO) -> tuple[str, ...]:
    """Return the row scope an ``expand`` operation produces."""
    if isinstance(expression, FieldReferenceDTO):
        return (
            expression.field.relation,
            expression.field.field,
            *expression.path,
        )
    if isinstance(expression, OperationExpressionDTO):
        if (
            expression.operator.name == "struct_field"
            and len(expression.arguments) == 1
        ):
            name = next(
                (
                    item.value for item in expression.parameters
                    if item.name == "name"
                ),
                None,
            )
            parent = expression.arguments[0]
            if isinstance(name, str) and name and _expands(parent):
                return (*_expand_scope(parent), name)
        if expression.operator.name == "expand" and expression.arguments:
            return _expand_scope(expression.arguments[0])
    document = expression_to_document(expression)
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"),
    ).encode()
    return ("expression", sha256(encoded).hexdigest())


def _expands(expression: ExpressionDTO) -> bool:
    if not isinstance(expression, OperationExpressionDTO):
        return False
    if expression.operator.name == "expand":
        return True
    if (
        expression.operator.name == "struct_field"
        and expression.arguments
    ):
        return _expands(expression.arguments[0])
    return False


def _row_semantics_source(
    expression: OperationExpressionDTO,
    row_effects: Mapping[str, RowEffectKind],
) -> str | None:
    name = expression.operator.name
    try:
        kind = row_effects[name]
    except KeyError as error:
        raise TypeError(
            f"cannot render operation {name!r}: its row effect is not known "
            "under this language composition"
        ) from error
    if kind == "preserve":
        return None
    if kind == "filter":
        return "RowSemantics('filter')"
    if name != "expand" or not expression.arguments:
        raise TypeError(
            f"cannot render the expanding operation {name!r}: its scope is "
            "not carried by the expression"
        )
    return f"RowSemantics('expand', scope={_expand_scope(expression.arguments[0])!r})"


def _render_node(
    expression: ExpressionDTO,
    row_effects: Mapping[str, RowEffectKind],
) -> str:
    """Render one expression DTO as an expression node."""
    if isinstance(expression, LiteralExpressionDTO):
        return f"as_expression({_literal_source(expression)}).model"
    if isinstance(expression, VariableExpressionDTO):
        return expression.name
    if isinstance(expression, FieldReferenceDTO):
        path = ", ".join(
            repr(part)
            for part in (expression.field.field, *expression.path)
        )
        return (
            "field_reference("
            f"source={expression.field.relation!r}, path=({path},), "
            f"logical_type={render_type(expression.logical_type)})"
        )
    if isinstance(expression, LookupExpressionDTO):
        return (
            "lookup_expression("
            f"ref_from_document({expression.relation.to_document()!r}), "
            f"key={_render_node(expression.key, row_effects)}, "
            f"target_field={expression.target_field!r}, "
            f"logical_type={render_type(expression.logical_type)})"
        )
    if isinstance(expression, OperationExpressionDTO):
        parts = [
            repr(expression.operator.name),
            *(
                _render_node(argument, row_effects)
                for argument in expression.arguments
            ),
        ]
        parts.extend(
            f"{parameter.name}={render_value(parameter.value)}"
            for parameter in expression.parameters
        )
        semantics = _row_semantics_source(expression, row_effects)
        if semantics is not None:
            parts.append(f"row_semantics={semantics}")
        parts.append(f"logical_type={render_type(expression.logical_type)}")
        return f"operation({', '.join(parts)})"
    raise TypeError(f"unsupported expression DTO {expression!r}")


def render(
    expression: ExpressionDTO,
    row_effects: Mapping[str, RowEffectKind] | None = None,
) -> str:
    """Render one expression DTO as a Selection or a transform variable."""
    effects = row_effects or {}
    if isinstance(expression, LiteralExpressionDTO):
        return _literal_source(expression)
    if isinstance(expression, VariableExpressionDTO):
        return expression.name
    return f"select_expression({_render_node(expression, effects)})"


def render_expression_source(
    dto: ExpressionDTO,
    row_effects: Mapping[str, RowEffectKind] | None = None,
) -> SourceFragment:
    """Render one expression DTO as an inline authoring expression.

    A value-expression slot receives a ``Selection``: a literal is already one,
    and a field read, lookup or operation is wrapped in ``select_expression``.
    Operation arguments are rendered as expression nodes so the low-level
    ``operation`` constructor stays valid. ``row_effects`` supplies the declared
    row effect of every operation the expression names.
    """
    body = render(dto, row_effects)
    imports = [
        "from kg_build_system import value_expression",
        "from kg_build_system.distribution.languages.expressions.service.internal import "
        "as_expression, select_expression",
        "from kg_build_system.distribution.languages.expressions.service.internal import "
        "field_reference, lookup_expression, operation",
        "from kg_build_system.distribution.model.public.refs import "
        "ref_from_document",
        "from kg_build_system import "
        "ArrayType, NullableType, "
        "BOOL, DATE, FLOAT, INT, STR, TIME, TIMESTAMP, UUID",
        "from kg_build_system.kernel.model.public.types import "
        "CustomType, StructType",
    ]
    if "RowSemantics(" in body:
        imports.append(
            "from kg_build_system.distribution.languages.expressions.model.internal "
            "import RowSemantics"
        )
    return SourceFragment("inline", body, tuple(imports))


__all__ = ["render_expression_source"]
