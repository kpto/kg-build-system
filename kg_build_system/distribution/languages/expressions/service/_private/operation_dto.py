"""Map an operation specification to its blueprint declaration DTO.

The specification is the live declaration: its argument and result rules may be
callables. The DTO records only what a declaration states statically, so a
callable expectation or resolver becomes ``None`` and the row-effect kind is
taken from the declared ``RowSemantics`` or ``RowEffectSpec``.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from kg_build_system.kernel.model.internal.json import freeze_json
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO
from kg_build_system.kernel.model.public.types import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
)
from kg_build_system.kernel.service.internal.types import type_to_dto

from ...model.internal.dto.operation_dto import (
    ArgumentDTO, ExpressionsPartDTO, OperationDTO, ParameterDTO, RowEffectKind,
)
from ...model.internal.model import RowSemantics
from ..internal.operations.spec import (
    ArgumentSpec, OperationSpec, ParameterSpec, RowEffectSpec,
)

_STATIC_TYPES = (UnitType, CustomType, StructType, ArrayType, NullableType)


def _expected_type(
    value: LogicalType | Callable[[tuple[LogicalType, ...]], LogicalType | None] | None,
) -> LogicalTypeDTO | None:
    """Return the declared static type, or ``None`` for a callable rule."""
    if value is None or isinstance(value, _STATIC_TYPES):
        return None if value is None else type_to_dto(value)
    return None


def _argument(specification: ArgumentSpec) -> ArgumentDTO:
    return ArgumentDTO(
        expected=_expected_type(specification.expected),
        description=specification.description,
    )


def _parameter(specification: ParameterSpec) -> ParameterDTO:
    return ParameterDTO(
        name=specification.name,
        required=specification.required,
        default=None if specification.required else freeze_json(specification.default),
    )


def _row_effect(
    value: RowEffectSpec | Callable[..., RowSemantics] | RowSemantics,
) -> RowEffectKind:
    if isinstance(value, RowSemantics):
        return value.mode
    if isinstance(value, RowEffectSpec):
        return value.kind
    return "preserve"


def operation_dto(specification: OperationSpec) -> OperationDTO:
    """Return the blueprint declaration of one operation specification.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            DEFAULT_OPERATIONS, operation_dto,
        )

        declaration = operation_dto(DEFAULT_OPERATIONS[0])
        assert declaration.name
        ```
    """
    declared = specification.result_type
    result_type = (
        None if declared is None or not isinstance(declared, _STATIC_TYPES)
        else type_to_dto(declared)
    )
    return OperationDTO(
        name=specification.name,
        arity=specification.arity,
        arguments=tuple(_argument(item) for item in specification.arguments),
        parameters=tuple(_parameter(item) for item in specification.parameters),
        result_type=result_type,
        row_effect=_row_effect(specification.row_effect),
    )


def expressions_part(
    specifications: Iterable[OperationSpec],
) -> ExpressionsPartDTO:
    """Return the expressions blueprint part for the supplied operations.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            DEFAULT_OPERATIONS, expressions_part,
        )

        part = expressions_part(DEFAULT_OPERATIONS)
        assert len(part.operations) == len(DEFAULT_OPERATIONS)
        ```
    """
    return ExpressionsPartDTO(
        operations=tuple(operation_dto(item) for item in specifications),
    )


__all__ = ["expressions_part", "operation_dto"]
