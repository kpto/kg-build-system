"""Map the authoring expression model to the expression blueprint DTO.

A field read names its field symbol and keeps the nested path below it; an
operation names its operation symbol. The document therefore carries identity,
never a bare source or operator string.
"""
from __future__ import annotations

from collections.abc import Iterator

from kg_build_system.distribution.model.public.refs import FieldRef, OperationRef
from kg_build_system.kernel import Key, SymbolRef
from kg_build_system.kernel.service.internal.types import type_to_dto

from ...model.internal.dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    LookupExpressionDTO, OperationExpressionDTO, OperationParameterDTO,
    VariableExpressionDTO,
)
from ...model.internal.model import (
    ExpressionNode, FieldReferenceExpression, LiteralExpression,
    LookupExpression, OperationExpression, VariableExpression,
)


def field_reference_for(source: str, path: tuple[str, ...]) -> tuple[FieldRef, tuple[str, ...]]:
    """Return the field reference and nested path of one authored read.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            field_reference_for,
        )

        field, path = field_reference_for("sites", ("site_name",))
        assert field.name == "sites.site_name"
        assert path == ()
        ```
    """
    if not path:
        raise ValueError("a field read requires a field path")
    return FieldRef("data", Key((f"{source}.{path[0]}",))), tuple(path[1:])


def expression_dto(value: ExpressionNode) -> ExpressionDTO:
    """Return the blueprint DTO of one authoring expression node."""
    common = {"logical_type": type_to_dto(value.logical_type)}
    if isinstance(value, LiteralExpression):
        return LiteralExpressionDTO(value=value.value, **common)
    if isinstance(value, VariableExpression):
        return VariableExpressionDTO(name=value.name, **common)
    if isinstance(value, FieldReferenceExpression):
        field, path = field_reference_for(value.source, value.path)
        return FieldReferenceDTO(field=field, path=path, **common)
    if isinstance(value, LookupExpression):
        return LookupExpressionDTO(
            relation=value.relation,
            target_field=value.target_field,
            key=expression_dto(value.key),
            **common,
        )
    if isinstance(value, OperationExpression):
        return OperationExpressionDTO(
            operator=OperationRef("expressions", Key((value.operator,))),
            arguments=tuple(expression_dto(argument) for argument in value.arguments),
            parameters=tuple(
                OperationParameterDTO(item.name, item.value)
                for item in value.parameters
            ),
            **common,
        )
    raise TypeError(f"unsupported expression model {value!r}")


def expression_field_path(expression: FieldReferenceDTO) -> tuple[str, ...]:
    """Return the full field path of one field read.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            expression_field_path,
        )

        path = expression_field_path(read)
        assert path[0] == "site_name"
        ```
    """
    return (expression.field.field, *expression.path)


def expression_references(expression: ExpressionDTO) -> tuple[SymbolRef, ...]:
    """Return the field and operation symbols one DTO tree reads.

    A derived row source is a plan identity, not a declared field, so its field
    references are omitted.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            expression_references,
        )

        references = expression_references(dto)
        ```
    """
    from ..internal.operations import DEFAULT_OPERATIONS

    references: list[SymbolRef] = []
    for node in walk_expression_dto(expression):
        if isinstance(node, FieldReferenceDTO):
            if not node.field.relation.startswith("derived:"):
                references.append(node.field.symbol)
        elif isinstance(node, LookupExpressionDTO):
            references.append(node.relation.symbol)
        elif isinstance(node, OperationExpressionDTO):
            if node.operator.name in DEFAULT_OPERATIONS:
                references.append(node.operator.symbol)
    return tuple(dict.fromkeys(references))


def walk_expression_dto(expression: ExpressionDTO) -> Iterator[ExpressionDTO]:
    """Yield an expression DTO tree in deterministic pre-order."""
    yield expression
    if isinstance(expression, LookupExpressionDTO):
        yield from walk_expression_dto(expression.key)
    if isinstance(expression, OperationExpressionDTO):
        for argument in expression.arguments:
            yield from walk_expression_dto(argument)


__all__ = [
    "expression_dto", "expression_field_path", "expression_references",
    "field_reference_for", "walk_expression_dto",
]
