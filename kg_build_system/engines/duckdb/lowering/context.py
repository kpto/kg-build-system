"""Lowering context: aliases, expansions, variables and lazy operands."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from sqlglot import exp

from .nodes import SqlNode

from ...._frozen_json import thaw_json
from ....expressions.ir import (
    ExpressionIR,
    OperationExpressionIR,
)
from ....types.ir import LogicalTypeIR
from ...protocols import ExpressionLowerer, Operand


def _parameter(expression: OperationExpressionIR, name: str) -> Any:
    for parameter in expression.parameters:
        if parameter.name == name:
            return thaw_json(parameter.value)
    raise ValueError(f"{expression.operator} requires parameter {name!r}")


@dataclass(frozen=True, slots=True)
class LazyOperand:
    """One operation argument, lowered only when the operator asks for it."""

    expression: ExpressionIR
    context: "DuckDBLoweringContext"

    @property
    def logical_type(self) -> LogicalTypeIR:
        return self.expression.logical_type

    def sql(self) -> SqlNode:
        return self.context.lower(self.expression)


@dataclass(frozen=True, slots=True)
class DuckDBLoweringContext:
    operators: Mapping[str, ExpressionLowerer[SqlNode]]
    aliases: Mapping[str, str] = field(default_factory=dict)
    expansions: Mapping[tuple[str, ...], SqlNode] = field(default_factory=dict)
    variables: Mapping[str, SqlNode] = field(default_factory=dict)

    def lower(self, expression: ExpressionIR) -> SqlNode:
        from .rendering import lower_expression

        return lower_expression(expression, self)

    def operand(self, expression: ExpressionIR) -> Operand[SqlNode]:
        return LazyOperand(expression, self)

    def parameter(self, expression: OperationExpressionIR, name: str) -> Any:
        return _parameter(expression, name)

    def alias_for(self, source: str) -> str:
        alias = self.aliases.get(source)
        if alias is None:
            raise ValueError(f"no scan alias for logical source {source!r}")
        return alias

    def expansion(self, scope: tuple[str, ...]) -> SqlNode:
        try:
            return self.expansions[scope].copy()
        except KeyError as error:
            raise ValueError(f"expansion scope {scope!r} was not planned") from error

    def with_variable(self, name: str, value: SqlNode) -> "DuckDBLoweringContext":
        return replace(self, variables={**self.variables, name: value})

    def with_aliases(self, aliases: Mapping[str, str]) -> "DuckDBLoweringContext":
        return replace(self, aliases={**self.aliases, **aliases})

    def with_expansion(
        self, scope: tuple[str, ...], value: SqlNode,
    ) -> "DuckDBLoweringContext":
        return replace(self, expansions={**self.expansions, scope: value})


__all__ = ["DuckDBLoweringContext", "LazyOperand"]
