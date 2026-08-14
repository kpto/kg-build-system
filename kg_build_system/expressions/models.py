"""Immutable expression domain model used by the authoring DSL."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, TypeAlias

from .._frozen_json import FrozenJson, FrozenObject, JsonScalar
from ..types import LogicalType


@dataclass(frozen=True, slots=True)
class RowEffect:
    """One ordered change to the row context of an expression."""

    mode: Literal["expand", "filter"]
    scope: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in {"expand", "filter"}:
            raise ValueError(f"unknown row-effect mode {self.mode!r}")
        if any(not part for part in self.scope):
            raise ValueError("row-semantic scope parts must be non-empty")
        if self.mode == "expand" and not self.scope:
            raise ValueError("expanding row semantics require a stable scope")
        if self.mode == "filter" and self.scope:
            raise ValueError("filtering row semantics may not declare a scope")


@dataclass(frozen=True, slots=True)
class RowSemantics:
    """The ordered row effects required to evaluate an expression."""

    mode: Literal["preserve", "expand", "filter"] = "preserve"
    scope: tuple[str, ...] = ()
    upstream: tuple[RowEffect, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in {"preserve", "expand", "filter"}:
            raise ValueError(f"unknown row-semantics mode {self.mode!r}")
        if any(not part for part in self.scope):
            raise ValueError("row-semantic scope parts must be non-empty")
        if self.mode == "expand" and not self.scope:
            raise ValueError("expanding row semantics require a stable scope")
        if self.mode != "expand" and self.scope:
            raise ValueError("only expanding row semantics may declare a scope")
        if self.mode == "preserve" and self.upstream:
            raise ValueError("preserving row semantics may not have upstream effects")

    @property
    def effects(self) -> tuple[RowEffect, ...]:
        if self.mode == "preserve":
            return ()
        return (*self.upstream, RowEffect(self.mode, self.scope))

    @classmethod
    def from_effects(cls, effects: tuple[RowEffect, ...]) -> "RowSemantics":
        if not effects:
            return cls()
        return cls(effects[-1].mode, effects[-1].scope, effects[:-1])


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
__all__ = [
    "Expression", "ExpressionNode", "FieldReferenceExpression", "FrozenJson", "FrozenObject",
    "JsonScalar", "LiteralExpression", "OperationExpression", "OperationParameter",
    "PRESERVE_ROWS", "RowEffect", "RowSemantics", "Traversal",
]
