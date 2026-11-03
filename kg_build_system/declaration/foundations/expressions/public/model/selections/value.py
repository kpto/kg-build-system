"""The value selection: one typed position in a row and its bindable value.

Example:
    ```python
    from kg_build_system import Field, Table, field

    class Row(Table):
        id: Field[str] = field(name="id")

    assert Row.id.expression.logical_type.name == "str"
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, cast

from .......kernel.internal.types import LogicalType
from ...._private.apply import apply_operation
from ...._private.descriptors import ExpressionDescriptor
from ...._private.selections import (
    SelectedMember, require_expression, select_expression,
)
from ..values import ValueExpression
from .types import NullableDataType

if TYPE_CHECKING:
    from ..arrays import ArrayExpression
    from ..boolean import BoolExpression
    from ..custom import CustomDataTypeExpression
    from ..nullable import NullableExpression
    from ..numeric import FloatExpression, IntExpression
    from ..structs import StructExpression
    from ..text import StrExpression
    from .effects import ArrayRowEffects, NullableRowEffects, RowEffects


TType_co = TypeVar("TType_co", covariant=True)


class ValueSelection(Generic[TType_co]):
    """A selectable value whose bindable calculation is exposed by ``expression``."""

    __slots__ = ("_value", "_member")
    expression: ExpressionDescriptor = ExpressionDescriptor()

    def __init__(
        self,
        value: ValueExpression[Any] | None = None,
        *,
        member: SelectedMember | None = None,
    ) -> None:
        if (value is None) == (member is None):
            raise TypeError("a selection requires exactly one expression or selected member")
        self._value = value
        self._member = member

    @property
    def model(self):
        """The canonical expression node behind this selection."""
        return require_expression(self).model

    @property
    def logical_type(self) -> LogicalType:
        """The canonical logical type of the selected position.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.logical_type.name == "str"
            ```
        """
        return (
            self._value.logical_type
            if self._value is not None
            else cast(SelectedMember, self._member).logical_type
        )

    def where_present(self) -> Self:
        """A present value is already present; the old API's narrowing is a no-op.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selection = Row.name
            assert selection.where_present() is selection
            ```
        """
        return self

    def default_to(self, value: Any) -> Self:
        """A present value needs no fallback; the old spelling is a no-op.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selection = Row.name
            assert selection.default_to("unknown") is selection
            ```
        """
        return self

    def drop_if(self, predicate: "Callable[[Self], BoolExpression]") -> Self:
        """Keep rows whose value satisfies a value-scoped predicate.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selected = Row.name.drop_if(
                lambda name: name.expression.equals("Depot")
            )
            assert selected.model.operator == "where_if"
            ```
        """
        if not callable(predicate):
            raise TypeError("drop_if requires a callable predicate")
        result = predicate(self)
        from ..boolean import BoolExpression

        if not isinstance(result, BoolExpression):
            raise TypeError("drop_if predicates must return a BoolExpression")
        selection = apply_operation(
            "where_if", require_expression(self), result.model
        )
        return cast(Self, select_expression(selection))

    def alter_rows(self) -> "RowEffects[Self]":
        """Opt in to the row-changing operations available on this selection.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selection = Row.name
            assert selection.alter_rows().selection is selection
            ```
        """
        from .effects import RowEffects

        return RowEffects(self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value or self._member!r})"


type ValueInput[T] = ValueSelection[T] | ValueExpression[T]


__all__ = ["ValueInput", "ValueSelection"]
