"""The operation declarations an expression tree refers to.

An operation is a declaration: its name, arity, positional arguments, named
parameters, result type and row effect. An expression tree names the operation
by reference and carries the result type it actually produced; this DTO records
the declaration beside it.

A callable result resolver or argument expectation has no static type, so the
DTO stores ``None`` for it. The expression node's ``logical_type`` remains the
actual result of one call.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from kg_build_system.kernel.model.internal.json import FrozenJson
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO

RowEffectKind = Literal["preserve", "filter", "expand"]


@dataclass(frozen=True, slots=True)
class ArgumentDTO:
    """One positional operation argument.

    ``expected`` is the declared logical type, or ``None`` when the operation
    resolves it from the argument types at call time. ``description`` is the
    declaration's human-readable name for the argument.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            ArgumentDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        argument = ArgumentDTO(expected=UnitTypeDTO("str"), description="value")
        ```
    """

    expected: LogicalTypeDTO | None
    description: str


@dataclass(frozen=True, slots=True)
class ParameterDTO:
    """One named operation parameter declaration.

    A required parameter has no default; an optional one carries its default as
    frozen JSON. The parameter's acceptance validator is not a declaration value
    and is not serialised.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            ParameterDTO,
        )

        parameter = ParameterDTO(name="separator", required=False, default=",")
        ```
    """

    name: str
    required: bool
    default: FrozenJson | None = None


@dataclass(frozen=True, slots=True)
class OperationDTO:
    """One operation declaration.

    ``arity`` is an exact count or a ``(minimum, maximum)`` pair whose maximum is
    ``None`` when unbounded. ``result_type`` is ``None`` when the operation
    resolves its result from the call, or declares none.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            ArgumentDTO, OperationDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        operation = OperationDTO(
            name="default_to",
            arity=2,
            arguments=(
                ArgumentDTO(UnitTypeDTO("str"), "value"),
                ArgumentDTO(UnitTypeDTO("str"), "fallback"),
            ),
            parameters=(),
            result_type=UnitTypeDTO("str"),
            row_effect="preserve",
        )
        ```
    """

    name: str
    arity: int | tuple[int, int | None]
    arguments: tuple[ArgumentDTO, ...]
    parameters: tuple[ParameterDTO, ...]
    result_type: LogicalTypeDTO | None
    row_effect: RowEffectKind

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("operations require a non-empty name")
        if self.row_effect not in {"preserve", "filter", "expand"}:
            raise ValueError(f"unknown row-effect kind {self.row_effect!r}")
        names = tuple(parameter.name for parameter in self.parameters)
        if len(names) != len(set(names)):
            raise ValueError("operation parameter names must be unique")


@dataclass(frozen=True, slots=True)
class ExpressionsPartDTO:
    """The expressions language's part of a blueprint: its operations.

    The part is empty when a document carries no operation declarations; an
    expression still names its operator by reference.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            ExpressionsPartDTO,
        )

        part = ExpressionsPartDTO()
        assert part.operations == ()
        ```
    """

    operations: tuple[OperationDTO, ...] = ()


__all__ = [
    "ArgumentDTO", "ExpressionsPartDTO", "OperationDTO", "ParameterDTO",
    "RowEffectKind",
]
