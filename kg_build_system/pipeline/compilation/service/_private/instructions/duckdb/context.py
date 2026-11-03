"""Emission context: aliases, expansions, variables and lazy operands."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from sqlglot import exp

from .sql import SqlNode

from kg_build_system.kernel.model.internal.json import thaw_json
from kg_build_system.declaration.foundations.expressions.model.internal import ExpressionDTO, OperationExpressionDTO
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO

if TYPE_CHECKING:
    from .protocols import ExpressionEmitter, Operand


def _parameter(expression: OperationExpressionDTO, name: str) -> Any:
    for parameter in expression.parameters:
        if parameter.name == name:
            return thaw_json(parameter.value)
    raise ValueError(f"{expression.operator} requires parameter {name!r}")


@dataclass(frozen=True, slots=True)
class LazyOperand:
    """One operation argument, emitted only when the operator asks for it."""

    expression: ExpressionDTO
    context: "DuckDbExpressionContext"

    @property
    def logical_type(self) -> LogicalTypeDTO:
        return self.expression.logical_type

    def sql(self) -> SqlNode:
        return self.context.emit(self.expression)


@dataclass(frozen=True, slots=True)
class DuckDbExpressionContext:
    operators: Mapping[str, ExpressionEmitter[SqlNode]]
    aliases: Mapping[str, str] = field(default_factory=dict)
    expansions: Mapping[tuple[str, ...], SqlNode] = field(default_factory=dict)
    variables: Mapping[str, SqlNode] = field(default_factory=dict)

    def emit(self, expression: ExpressionDTO) -> SqlNode:
        from .rendering import emit_expression

        return emit_expression(expression, self)

    def operand(self, expression: ExpressionDTO) -> Operand[SqlNode]:
        return LazyOperand(expression, self)

    def parameter(self, expression: OperationExpressionDTO, name: str) -> Any:
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

    def with_variable(self, name: str, value: SqlNode) -> "DuckDbExpressionContext":
        return replace(self, variables={**self.variables, name: value})

    def with_aliases(self, aliases: Mapping[str, str]) -> "DuckDbExpressionContext":
        return replace(self, aliases={**self.aliases, **aliases})

    def with_expansion(
        self, scope: tuple[str, ...], value: SqlNode,
    ) -> "DuckDbExpressionContext":
        return replace(self, expansions={**self.expansions, scope: value})


__all__ = ["DuckDbExpressionContext", "LazyOperand"]
