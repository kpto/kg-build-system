"""Internal wrappers over the expressions blueprint-part declaration mapping."""
from __future__ import annotations

from collections.abc import Iterable

from ...model.internal.dto.operation_dto import ExpressionsPartDTO, OperationDTO
from .operations import OperationSpec


def operation_dto(specification: OperationSpec) -> OperationDTO:
    """Return the blueprint declaration of one operation specification.

    The result type is ``None`` when the specification resolves it from a call.
    """
    from .._private.operation_dto import operation_dto as implementation

    return implementation(specification)


def expressions_part(
    specifications: Iterable[OperationSpec],
) -> ExpressionsPartDTO:
    """Return the expressions blueprint part for the supplied operations."""
    from .._private.operation_dto import expressions_part as implementation

    return implementation(specifications)


__all__ = ["expressions_part", "operation_dto"]
