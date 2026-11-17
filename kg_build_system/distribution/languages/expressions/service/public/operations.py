"""Author-facing operation handles for project-local operations.

An ``OperationSpec`` is a runtime declaration: its arity, argument rules and
result type are values. ``Operation`` pairs that declaration with a typed
callable signature, so a project can wrap its own spec once and use the handle
with ``severity_rank(selection)`` or ``selection.custom_op(severity_rank)``.

Example:
    ```python
    from kg_build_system.distribution.languages.expressions.service.public import (
        ArgumentSpec, Operation, OperationSpec,
    )
    from kg_build_system import INT, STR

    spec = OperationSpec(
        name="severity_rank", arity=1,
        arguments=(ArgumentSpec(expected=STR),), result_type=INT,
    )
    severity_rank = Operation(spec)
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ...model.public.selection import Selection
from ..internal.operations import (
    ArgumentSpec,
    DEFAULT_OPERATIONS,
    OperationRegistry,
    OperationSpec,
    ParameterSpec,
    RowEffectSpec,
)
from ..internal.selections import select_expression


@dataclass(frozen=True, slots=True)
class Operation[**P, R]:
    """A typed callable handle over one runtime operation specification.

    The handle is the authoring form of a project-local operation. Its type
    parameters are the operation's argument types and its result type, so the
    handle call and ``Selection.custom_op`` share one precise signature.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.public import (
            Selection,
        )
        from kg_build_system.distribution.languages.expressions.service.public import (
            Operation,
        )

        severity_rank: Operation[[Selection[str]], int] = Operation(spec)
        ```
    """

    spec: OperationSpec

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Selection[R]:
        """Build the selection for one operation call.

        Example:
            ```python
            selected = severity_rank(selection)
            ```
        """
        return apply_operation(self.spec, *args, **kwargs)


def apply_operation[R, **P](
    spec: OperationSpec, *arguments: P.args, **parameters: P.kwargs,
) -> Selection[R]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Apply one operation specification and wrap the result as a selection.

    The specification value is used directly; no global operation name lookup
    participates in the call.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.public import (
            apply_operation,
        )

        selected: Selection[int] = apply_operation(spec, selection)
        ```
    """
    expression = spec.apply(*arguments, **parameters)
    return cast("Selection[R]", select_expression(expression))


__all__ = [
    "ArgumentSpec", "DEFAULT_OPERATIONS", "Operation", "OperationRegistry",
    "OperationSpec", "ParameterSpec", "RowEffectSpec", "apply_operation",
]
