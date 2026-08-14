"""Canonical, immutable expression intermediate representation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, TypeAlias

from ..types import LogicalType


type JsonScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class FrozenObject:
    items: tuple[tuple[str, "FrozenJson"], ...]


type FrozenJson = JsonScalar | tuple["FrozenJson", ...] | FrozenObject


@dataclass(frozen=True, slots=True)
class RowSemantics:
    """How evaluating an expression affects its containing relational row."""

    mode: Literal["preserve", "expand", "filter"] = "preserve"
    scope: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in {"preserve", "expand", "filter"}:
            raise ValueError(f"unknown row-semantics mode {self.mode!r}")
        if any(not part for part in self.scope):
            raise ValueError("row-semantic scope parts must be non-empty")
        if self.mode == "expand" and not self.scope:
            raise ValueError("expanding row semantics require a stable scope")
        if self.mode != "expand" and self.scope:
            raise ValueError("only expanding row semantics may declare a scope")


PRESERVE_ROWS = RowSemantics()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpressionNode:
    """Shared state carried by every canonical expression node."""

    logical_type: LogicalType
    row_semantics: RowSemantics = PRESERVE_ROWS


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpression(ExpressionNode):
    value: FrozenJson


@dataclass(frozen=True, slots=True)
class Traversal:
    """One structured or collection-valued segment of a field path."""

    kind: Literal["struct", "array"]
    path: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind not in {"struct", "array"}:
            raise ValueError(f"unknown traversal kind {self.kind!r}")
        if not self.path or any(not part for part in self.path):
            raise ValueError("traversal paths must contain non-empty parts")


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldReferenceExpression(ExpressionNode):
    source: str
    path: tuple[str, ...]
    traversals: tuple[Traversal, ...] = ()

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("field references require a source")
        if not self.path or any(not part for part in self.path):
            raise ValueError("field-reference paths must contain non-empty parts")
        for traversal in self.traversals:
            if self.path[: len(traversal.path)] != traversal.path:
                raise ValueError("each traversal path must be a prefix of the field path")


@dataclass(frozen=True, slots=True)
class OperationParameter:
    name: str
    value: FrozenJson

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("operation parameter names must be non-empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExpression(ExpressionNode):
    operator: str
    arguments: tuple[ExpressionNode, ...]
    parameters: tuple[OperationParameter, ...] = ()

    def __post_init__(self) -> None:
        if not self.operator:
            raise ValueError("operations require a stable operator name")
        names = tuple(parameter.name for parameter in self.parameters)
        if len(names) != len(set(names)):
            raise ValueError("operation parameter names must be unique")
        if names != tuple(sorted(names)):
            object.__setattr__(self, "parameters", tuple(sorted(self.parameters, key=lambda item: item.name)))

    def with_arguments(self, arguments: tuple[ExpressionNode, ...]) -> "OperationExpression":
        return self if arguments == self.arguments else replace(self, arguments=arguments)


Expression: TypeAlias = LiteralExpression | FieldReferenceExpression | OperationExpression
ExpressionIR: TypeAlias = Expression


__all__ = [
    "Expression", "ExpressionIR", "ExpressionNode", "FieldReferenceExpression", "FrozenJson", "FrozenObject",
    "JsonScalar", "LiteralExpression", "OperationExpression", "OperationParameter",
    "PRESERVE_ROWS", "RowSemantics", "Traversal",
]
