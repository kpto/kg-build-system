"""The operation specification: arity, arguments, result type and row effect.

An operation is one spec. The authoring methods call ``spec.apply``; the DTO only
records the operator name, arguments, parameters and result type. A custom
operation is therefore one spec plus one instruction emitter, with no dispatcher edit.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from .......kernel.internal.json import freeze_json
from ...._private.literals import literal
from ...model import ExpressionNode, OperationExpression, OperationParameter, RowSemantics
from ...._private.semantics import compose_row_semantics
from .......kernel.internal.types import LogicalType

if TYPE_CHECKING:
    from ....public.model.values import ValueExpression


_ARITY: TypeAlias = int | tuple[int, int | None]


class _Missing:
    """Marker for an operation parameter with no default."""


_MISSING = _Missing()


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
    default: Any = _MISSING
    accepts: Callable[[Any], bool] | None = None

    @property
    def required(self) -> bool:
        return self.default is _MISSING


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
        if self.kind == "expand":
            if self.scope is None:
                raise TypeError("expanding row effects require a scope resolver")
            scope = self.scope(nodes, types, parameters)
            if not scope:
                raise ValueError("expanding row effects require a non-empty scope")
            return RowSemantics("expand", scope)
        return RowSemantics("filter")


@dataclass(frozen=True, slots=True)
class OperationSpec:
    """The single declaration of one operation."""

    name: str
    arity: _ARITY
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
        if isinstance(self.arity, int):
            return count == self.arity
        minimum, maximum = self.arity
        return count >= minimum and (maximum is None or count <= maximum)

    def _arity_message(self) -> str:
        if isinstance(self.arity, int):
            return f"{self.name} requires {self.arity} arguments"
        minimum, maximum = self.arity
        if maximum is None:
            return f"{self.name} requires at least {minimum} arguments"
        return f"{self.name} requires between {minimum} and {maximum} arguments"

    def _argument_spec(self, index: int) -> ArgumentSpec | None:
        if index < len(self.arguments):
            return self.arguments[index]
        if self.repeat_last_argument and self.arguments:
            return self.arguments[-1]
        return None

    def _coerce(self, value: Any, index: int, types: tuple[LogicalType, ...]) -> ExpressionNode:
        if isinstance(value, ExpressionNode):
            return value
        model = getattr(value, "model", None)
        if isinstance(model, ExpressionNode):
            return model
        spec = self._argument_spec(index)
        expected: LogicalType | None = None
        if spec is not None and spec.expected is not None:
            expected = (
                spec.expected(types)
                if callable(spec.expected)
                else spec.expected
            )
        return literal(value, logical_type=expected)

    def _parameters(self, values: Mapping[str, Any]) -> dict[str, Any]:
        declared = {parameter.name: parameter for parameter in self.parameters}
        unknown = set(values) - set(declared)
        if unknown:
            raise TypeError(
                f"{self.name} received unknown parameters {sorted(unknown)}"
            )
        resolved: dict[str, Any] = {}
        for parameter in self.parameters:
            if parameter.name in values:
                value = values[parameter.name]
            elif parameter.required:
                raise TypeError(
                    f"{self.name} requires parameter {parameter.name!r}"
                )
            else:
                value = parameter.default
            if parameter.accepts is not None and not parameter.accepts(value):
                raise ValueError(
                    f"{self.name} parameter {parameter.name!r} has invalid value {value!r}"
                )
            resolved[parameter.name] = value
        return resolved

    def _validate_types(
        self,
        nodes: tuple[ExpressionNode, ...],
        parameters: Mapping[str, Any],
    ) -> tuple[LogicalType, ...]:
        types = tuple(node.logical_type for node in nodes)
        for index, logical_type in enumerate(types):
            spec = self._argument_spec(index)
            if spec is not None and spec.accepts is not None and not spec.accepts(logical_type):
                raise TypeError(
                    f"{self.name} argument {index + 1} has logical type "
                    f"{logical_type!r}, which is not a valid {spec.description}"
                )
        if self.validate_arguments is not None:
            self.validate_arguments(nodes, parameters)
        return types

    def result(self, types: tuple[LogicalType, ...], parameters: Mapping[str, Any]) -> LogicalType:
        """Resolve the result logical type for one argument type tuple."""
        if self.result_type is None:
            raise TypeError(f"{self.name} requires an explicit result type")
        if callable(self.result_type):
            return self.result_type(types, parameters)
        return self.result_type

    def semantics(
        self,
        nodes: tuple[ExpressionNode, ...],
        types: tuple[LogicalType, ...],
        parameters: Mapping[str, Any],
    ) -> RowSemantics:
        """Resolve the local row effect declared by this operation."""
        if isinstance(self.row_effect, RowEffectSpec):
            return self.row_effect.semantics(nodes, types, parameters)
        if callable(self.row_effect):
            return self.row_effect(nodes, types, parameters)
        return self.row_effect

    def apply(
        self,
        *arguments: Any,
        result_type: LogicalType | None = None,
        **parameters: Any,
    ) -> "ValueExpression[Any]":
        """Build a typed authoring expression, validating the call first."""
        if not self.accepts_arity(len(arguments)):
            raise TypeError(self._arity_message())
        resolved_parameters = self._parameters(parameters)
        nodes: list[ExpressionNode] = []
        for index, value in enumerate(arguments):
            node = self._coerce(value, index, tuple(item.logical_type for item in nodes))
            nodes.append(node)
        frozen_nodes = tuple(nodes)
        types = self._validate_types(frozen_nodes, resolved_parameters)
        resolved_type = result_type or self.result(types, resolved_parameters)
        local = self.semantics(frozen_nodes, types, resolved_parameters)
        expression = OperationExpression(
            operator=self.name,
            arguments=frozen_nodes,
            parameters=tuple(
                OperationParameter(name, freeze_json(value))
                for name, value in sorted(resolved_parameters.items())
                if value is not _MISSING
            ),
            logical_type=resolved_type,
            row_semantics=compose_row_semantics(*frozen_nodes, local=local),
        )
        from ....public.service.expression import wrap_expression

        return wrap_expression(expression)


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
