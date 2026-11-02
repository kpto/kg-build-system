"""Engine-neutral protocols for lowering expressions and row-source plans.

An engine supplies one implementation per operator and one per row-source plan
node. The dispatcher only looks a name or a node type up in a registry; it never
tests the operator itself. A new operator is a new implementation plus one
registration.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar

from ...expressions.internal.ir import ExpressionIR, OperationExpressionIR
from ...types.internal.ir import LogicalTypeIR


NodeT = TypeVar("NodeT")
NodeT_co = TypeVar("NodeT_co", covariant=True)
NodeT_contra = TypeVar("NodeT_contra", contravariant=True)


class Operand(Protocol[NodeT_co]):
    """One argument of an operation, lowered on demand.

    Lazy access is what lets an operator such as ``transform_items`` build a
    lambda body in a child scope; a dispatcher that rendered every argument
    eagerly could not express it.
    """

    @property
    def expression(self) -> ExpressionIR: ...

    @property
    def logical_type(self) -> LogicalTypeIR: ...

    def sql(self) -> NodeT_co: ...


class LoweringContext(Protocol[NodeT]):
    """What one expression lowerer may ask of its surroundings."""

    def lower(self, expression: ExpressionIR) -> NodeT: ...

    def parameter(self, expression: OperationExpressionIR, name: str) -> Any: ...

    def alias_for(self, source: str) -> str: ...

    def expansion(self, scope: tuple[str, ...]) -> NodeT: ...

    def with_variable(self, name: str, value: NodeT) -> "LoweringContext[NodeT]": ...


class ExpressionLowerer(Protocol[NodeT]):
    """One expression operator, rendered by the engine that owns it."""

    @property
    def operator(self) -> str: ...

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[NodeT]],
        context: LoweringContext[NodeT],
    ) -> NodeT: ...


class RowSourceContext(Protocol[NodeT_co]):
    """What one row-source lowerer may ask of its surroundings."""

    def relation_for(self, plan: Any) -> str: ...

    def shape_for(self, plan: Any) -> tuple[Any, ...]: ...

    def source_key(self, plan: Any) -> str: ...

    def lower_expression(
        self, expression: ExpressionIR, aliases: Mapping[str, str],
    ) -> NodeT_co: ...


class RowSourceLowerer(Protocol[NodeT_contra]):
    """One row-source plan node, rendered as a relation expression."""

    @property
    def node_type(self) -> type[Any]: ...

    def lower(self, plan: Any, context: RowSourceContext[NodeT_contra]) -> str: ...


class ExpressionLowering(Protocol[NodeT]):
    """The complete set of expression operators an engine understands."""

    @property
    def operators(self) -> Mapping[str, ExpressionLowerer[NodeT]]: ...


__all__ = [
    "ExpressionLowerer",
    "ExpressionLowering",
    "LoweringContext",
    "NodeT",
    "NodeT_co",
    "NodeT_contra",
    "Operand",
    "RowSourceContext",
    "RowSourceLowerer",
]
