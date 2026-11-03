"""The operation specification: arity, arguments, result type and row effect.

An operation is one spec. The authoring methods call ``spec.apply``; the DTO only
records the operator name, arguments, parameters and result type. A custom
operation is therefore one spec plus one instruction emitter, with no dispatcher edit.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from .......kernel.internal.types import LogicalType
from ...model import ExpressionNode, OperationExpression, RowSemantics

if TYPE_CHECKING:
    from ....public.model.values import ValueExpression


Arity: TypeAlias = int | tuple[int, int | None]


class Missing:
    """Marker for an operation parameter with no default."""


MISSING = Missing()


@dataclass(frozen=True, slots=True)
class ArgumentSpec:
    """How one positional argument is validated and inferred."""

    expected: LogicalType | Callable[[tuple[LogicalType, ...]], LogicalType | None] | None = None
    accepts: Callable[[LogicalType], bool] | None = None
    description: str = "expression"


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """One named operation parameter and its validation rule."""

    name: str
    default: Any = MISSING
    accepts: Callable[[Any], bool] | None = None

    @property
    def required(self) -> bool:
        return self.default is MISSING


ResultTypeResolver: TypeAlias = Callable[
    [tuple[LogicalType, ...], Mapping[str, Any]], LogicalType
]
RowEffectResolver: TypeAlias = Callable[
    [tuple[ExpressionNode, ...], tuple[LogicalType, ...], Mapping[str, Any]],
    RowSemantics,
]
ScopeResolver: TypeAlias = Callable[
    [tuple[ExpressionNode, ...], tuple[LogicalType, ...], Mapping[str, Any]],
    tuple[str, ...],
]
ArgumentValidator: TypeAlias = Callable[
    [tuple[ExpressionNode, ...], Mapping[str, Any]], None
]


@dataclass(frozen=True, slots=True)
class RowEffectSpec:
    """The row effect an operation declares, in a form a planner can inspect.

    ``scope`` is evaluated when the expression is built; ``predicate_index``
    names the filter predicate. A presence filter leaves it unset and filters on
    the operation's first argument.
    """

    kind: Literal["expand", "filter"]
    predicate_index: int | None = None
    scope: ScopeResolver | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"expand", "filter"}:
            raise ValueError(f"unknown row-effect kind {self.kind!r}")

    def semantics(
        self,
        nodes: tuple[ExpressionNode, ...],
        types: tuple[LogicalType, ...],
        parameters: Mapping[str, Any],
    ) -> RowSemantics:
        from ...._private.operations import resolve_row_effect_spec

        return resolve_row_effect_spec(self, nodes, types, parameters)


@dataclass(frozen=True, slots=True)
class OperationSpec:
    """The single declaration of one operation."""

    name: str
    arity: Arity
    arguments: tuple[ArgumentSpec, ...] = ()
    parameters: tuple[ParameterSpec, ...] = ()
    result_type: ResultTypeResolver | LogicalType | None = None
    row_effect: RowEffectSpec | RowEffectResolver | RowSemantics = RowSemantics()
    repeat_last_argument: bool = False
    validate_arguments: ArgumentValidator | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("operations require a non-empty name")
        if isinstance(self.arity, int):
            minimum = maximum = self.arity
        else:
            minimum, maximum = self.arity
            if maximum is not None and maximum < minimum:
                raise ValueError("operation maximum arity must not be below its minimum")
        if minimum < 0:
            raise ValueError("operation arity must not be negative")
        names = tuple(parameter.name for parameter in self.parameters)
        if len(names) != len(set(names)):
            raise ValueError("operation parameter names must be unique")
        if any(not name for name in names):
            raise ValueError("operation parameter names must be non-empty")

    def accepts_arity(self, count: int) -> bool:
        from ...._private.operations import accepts_arity

        return accepts_arity(self, count)

    def result(self, types: tuple[LogicalType, ...], parameters: Mapping[str, Any]) -> LogicalType:
        """Resolve the result logical type for one argument type tuple."""
        from ...._private.operations import resolve_result

        return resolve_result(self, types, parameters)

    def semantics(
        self,
        nodes: tuple[ExpressionNode, ...],
        types: tuple[LogicalType, ...],
        parameters: Mapping[str, Any],
    ) -> RowSemantics:
        """Resolve the local row effect declared by this operation."""
        from ...._private.operations import resolve_semantics

        return resolve_semantics(self, nodes, types, parameters)

    def apply(
        self,
        *arguments: Any,
        result_type: LogicalType | None = None,
        **parameters: Any,
    ) -> "ValueExpression[Any]":
        """Build a typed authoring expression, validating the call first."""
        from ...._private.operations import apply

        return apply(self, *arguments, result_type=result_type, **parameters)


@dataclass(frozen=True, slots=True)
class OperationRegistry:
    """An immutable, name-keyed set of operation specs."""

    specs: tuple[OperationSpec, ...] = ()

    def __post_init__(self) -> None:
        names = tuple(spec.name for spec in self.specs)
        if len(names) != len(set(names)):
            raise ValueError("operation names must be unique")

    @property
    def by_name(self) -> dict[str, OperationSpec]:
        return {spec.name: spec for spec in self.specs}

    def __getitem__(self, name: str) -> OperationSpec:
        try:
            return self.by_name[name]
        except KeyError as error:
            raise KeyError(f"unknown expression operation {name!r}") from error

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.by_name

    def __len__(self) -> int:
        return len(self.specs)

    def __iter__(self) -> Iterator[OperationSpec]:
        return iter(self.specs)

    def get(
        self, name: str, default: OperationSpec | None = None,
    ) -> OperationSpec | None:
        return self.by_name.get(name, default)

    def keys(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.specs)

    def values(self) -> tuple[OperationSpec, ...]:
        return self.specs

    def items(self) -> tuple[tuple[str, OperationSpec], ...]:
        return tuple((spec.name, spec) for spec in self.specs)

    def names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.specs)

    def register(self, *specs: OperationSpec) -> "OperationRegistry":
        return OperationRegistry((*self.specs, *specs))


__all__ = [
    "ArgumentSpec", "OperationRegistry", "OperationSpec", "ParameterSpec",
    "RowEffectSpec",
]
