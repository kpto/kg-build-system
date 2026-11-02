"""Framework-internal interface of the relational planning domain.

The planner produces engine-neutral plans. An engine lowers those plans, so the
protocols here state only what a plan lowerer is asked for; they name no SQL type
and no engine.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar

from ..expressions.interfaces import ExpressionNode as DomainExpressionNode
from ..expressions.ir import ExpressionIR, OperationExpressionIR
from ..table.ir import RowSourcePlanIR
from .ir import ExpandIR, FilterIR, RelationPlanIR, ScanIR
from .planner import (
    expansion_scope as _expansion_scope,
    lower_product as _lower_product,
)

ResultT = TypeVar("ResultT", covariant=True)


def lower_product(
    outputs: Mapping[str, ExpressionIR | DomainExpressionNode],
    relations: Mapping[str, str],
    *,
    predicates: tuple[ExpressionIR, ...] = (),
) -> RelationPlanIR:
    """Plan one projection or binding without leaking its row effects elsewhere.

    Every output and predicate contributes its row effects to this plan only. The
    plan reads the single driving source its expressions reference; a second
    source is refused and must be introduced by an explicit lookup instead.

    Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.expressions.interfaces import expression_to_ir
    from kg_build_system.relational.interfaces import lower_product

    expression = expression_to_ir(value_expression(42).model)
    plan = lower_product({"answer": expression}, {})
    print(plan.outputs[0][0])
    # answer
    ```
    """
    return _lower_product(outputs, relations, predicates=predicates)


def expansion_scope(expression: OperationExpressionIR) -> tuple[str, ...]:
    """Derive a stable, plan-local identity for one explicit ``expand`` operation.

    A field or struct-field argument names its scope directly. Any other argument
    is identified by a digest of its canonical expression encoding, so the same
    expansion written twice shares one scope.

    Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.expressions import select_expression
    from kg_build_system.expressions.interfaces import expression_to_ir
    from kg_build_system.relational.interfaces import expansion_scope
    from kg_build_system.types import ArrayType, INT

    expanded = select_expression(
        value_expression([1, 2], logical_type=ArrayType(INT))
    ).expand()
    scope = expansion_scope(expression_to_ir(expanded.model))
    print(scope[0])
    # expression
    ```
    """
    return _expansion_scope(expression)


class RelationPlanLowerer(Protocol[ResultT]):
    """Render one planned relational product for an execution engine."""

    def lower_plan(self, plan: RelationPlanIR) -> ResultT:
        """Render a self-contained relation plan in the engine's result type."""
        ...


class RowSourcePlanLowerer(Protocol[ResultT]):
    """Render one row-source plan over relations the caller already named."""

    def lower_row_source(
        self,
        plan: RowSourcePlanIR,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[Any, ...]],
    ) -> ResultT:
        """Render a row-source plan over ``relations`` and its row ``shapes``."""
        ...


class PlanLowerer(RelationPlanLowerer[ResultT], RowSourcePlanLowerer[ResultT], Protocol[ResultT]):
    """The complete lowering surface an engine offers for neutral plans."""


__all__ = [
    "ExpandIR",
    "FilterIR",
    "PlanLowerer",
    "RelationPlanIR",
    "RelationPlanLowerer",
    "RowSourcePlanIR",
    "RowSourcePlanLowerer",
    "ScanIR",
    "expansion_scope",
    "lower_product",
]
