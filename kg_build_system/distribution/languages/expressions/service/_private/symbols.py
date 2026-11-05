"""Project the expression language declarations into linked symbols."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.distribution.model.public.refs import FieldRef, OperationRef
from kg_build_system.kernel import Declaration, Key, Symbol, SymbolRef

from ...model.internal.model import (
    ExpressionNode, FieldReferenceExpression, LookupExpression,
    OperationExpression,
)
from ..internal.operations import DEFAULT_OPERATIONS, OperationSpec
from .visitors import walk_expression


def operation_reference(name: str) -> OperationRef:
    """Return the reference of one operation symbol.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            operation_reference,
        )

        assert operation_reference("default_to").name == "default_to"
        ```
    """
    return OperationRef("expressions", Key((name,)))


def spec_of(declaration: Declaration) -> OperationSpec:
    """Return the operation specification one declaration carries.

    Example:
        ```python
        from kg_build_system.kernel import Declaration

        spec = spec_of(Declaration(operation_spec))
        ```
    """
    value = declaration.value
    if not isinstance(value, OperationSpec):
        raise TypeError(
            f"expression declaration {value!r} is not an operation spec"
        )
    return value


def authoring_references(value: ExpressionNode) -> tuple[SymbolRef, ...]:
    """Return the field and operation symbols one authoring tree reads.

    Example:
        ```python
        references = authoring_references(expression)
        ```
    """
    references: list[SymbolRef] = []
    for node in walk_expression(value):
        if isinstance(node, FieldReferenceExpression):
            if not node.source.startswith("derived:"):
                references.append(
                    FieldRef(
                        "data", Key((f"{node.source}.{node.path[0]}",)),
                    ).symbol
                )
        elif isinstance(node, LookupExpression):
            references.append(node.relation.symbol)
        elif (
            isinstance(node, OperationExpression)
            and node.operator in DEFAULT_OPERATIONS
        ):
            references.append(operation_reference(node.operator).symbol)
    return tuple(dict.fromkeys(references))


def symbols_for_declarations(
    declarations: Sequence[Declaration],
) -> Mapping[SymbolRef, Symbol]:
    """Return one operation symbol per declaration.

    Example:
        ```python
        symbols = symbols_for_declarations(declarations)
        ```
    """
    symbols: dict[SymbolRef, Symbol] = {}
    for declaration in declarations:
        spec = spec_of(declaration)
        reference = operation_reference(spec.name)
        symbols[reference.symbol] = Symbol(
            reference.key, "operation", spec,
        )
    return symbols


__all__ = [
    "authoring_references", "operation_reference", "spec_of",
    "symbols_for_declarations",
]
