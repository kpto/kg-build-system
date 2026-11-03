"""Engine protocols for emitting expressions and row-source plans as SQL.

An engine supplies one implementation per operator and one per row-source plan
node. The dispatcher only looks a name or a node type up in a registry; it never
tests the operator itself. A new operator is a new implementation plus one
registration.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar

from kg_build_system.declaration.foundations.expressions.model.internal import ExpressionDTO, OperationExpressionDTO
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


NodeT = TypeVar("NodeT")
NodeT_co = TypeVar("NodeT_co", covariant=True)
NodeT_contra = TypeVar("NodeT_contra", contravariant=True)


class Operand(Protocol[NodeT_co]):
    """One argument of an operation, emitted on demand.

    Lazy access is what lets an operator such as ``transform_items`` build a
    lambda body in a child scope; a dispatcher that rendered every argument
    eagerly could not express it.
    """

    @property
    def expression(self) -> ExpressionDTO: ...

    @property
    def logical_type(self) -> LogicalTypeDTO: ...

    def sql(self) -> NodeT_co: ...


class EmissionContext(Protocol[NodeT]):
    """What one expression emitter may ask of its surroundings."""

    def emit(self, expression: ExpressionDTO) -> NodeT: ...

    def parameter(self, expression: OperationExpressionDTO, name: str) -> Any: ...

    def alias_for(self, source: str) -> str: ...

    def expansion(self, scope: tuple[str, ...]) -> NodeT: ...

    def with_variable(self, name: str, value: NodeT) -> "EmissionContext[NodeT]": ...


class ExpressionEmitter(Protocol[NodeT]):
    """One expression operator, emitted by the engine that owns it."""

    @property
    def operator(self) -> str: ...

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[NodeT]],
        context: EmissionContext[NodeT],
    ) -> NodeT: ...


class RowSourceEmissionContext(Protocol[NodeT_co]):
    """What one row-source emitter may ask of its surroundings."""

    def relation_for(self, plan: Any) -> str: ...

    def shape_for(self, plan: Any) -> tuple[Any, ...]: ...

    def source_key(self, plan: Any) -> str: ...

    def emit_expression(
        self, expression: ExpressionDTO, aliases: Mapping[str, str],
    ) -> NodeT_co: ...


class RowSourceEmitter(Protocol[NodeT_contra]):
    """One row-source plan node, emitted as a relation expression."""

    @property
    def node_type(self) -> type[Any]: ...

    def emit(self, plan: Any, context: RowSourceEmissionContext[NodeT_contra]) -> str: ...


__all__ = [
    "EmissionContext",
    "ExpressionEmitter",
    "NodeT",
    "NodeT_co",
    "NodeT_contra",
    "Operand",
    "RowSourceEmissionContext",
    "RowSourceEmitter",
]
