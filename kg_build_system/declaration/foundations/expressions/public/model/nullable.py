"""Bindable nullable expression family.

Null policy belongs to selections. A nullable expression preserves absence
and exposes no narrowing operation. It carries only the text key helpers the
compatibility surface needs; their results stay nullable.

Example:
    ```python
    from kg_build_system import Field, Table, field

    class Row(Table):
        name: Field[str | None] = field(name="name")

    assert Row.name.expression.append("!").model.operator == "concat"
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from ......kernel.internal.types import STR, Nullable, NullableType
from ..._private.apply import apply_operation
from ..._private.coercion import expression_input
from ...internal.model import ExpressionNode
from .values import NullableAuthoringInput, ValueExpression

if TYPE_CHECKING:
    from .boolean import BoolExpression
    from .text import StrExpression


TData = TypeVar("TData")
TNonNullExpr = TypeVar("TNonNullExpr", bound=ValueExpression)


class NullableExpression(
    ValueExpression[Nullable[TData]],
    NullableAuthoringInput[TData | None],
    Generic[TData, TNonNullExpr],
):
    """Bindable nullable calculation with a known non-null expression family."""

    __slots__ = ("_non_null_factory",)

    def __init__(
        self,
        model: ExpressionNode,
        non_null_factory: Callable[[ExpressionNode], TNonNullExpr],
    ) -> None:
        if not isinstance(model.logical_type, NullableType):
            raise TypeError("NullableExpression requires a nullable logical type")
        super().__init__(model)
        self._non_null_factory = non_null_factory

    @property
    def non_null_logical_type(self):
        logical_type = self.logical_type
        assert isinstance(logical_type, NullableType)
        return logical_type.value

    # Compatibility spelling for callers that build a text key directly on a
    # nullable source read (``row.id.expression.append(...)``). The result is
    # still nullable: these methods preserve absence rather than hiding it.
    def append(self, value: str | ValueExpression[str]) -> "NullableExpression[str, StrExpression]":
        """Place another string after this one; absence is preserved.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.expression.append("!").model.operator == "concat"
            ```
        """
        return cast(
            "NullableExpression[str, StrExpression]",
            apply_operation("concat", self.model, expression_input(value, STR)),
        )

    def prepend(self, value: str | ValueExpression[str]) -> "NullableExpression[str, StrExpression]":
        """Place another string in front of this one; absence is preserved.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.expression.prepend("kg:").model.operator == "concat"
            ```
        """
        return cast(
            "NullableExpression[str, StrExpression]",
            apply_operation("concat", expression_input(value, STR), self.model),
        )

    def replace(self, search: str, replacement: str) -> "NullableExpression[str, StrExpression]":
        """Replace every occurrence of ``search``; absence is preserved.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.expression.replace("-", "_").model.operator == "replace"
            ```
        """
        return cast(
            "NullableExpression[str, StrExpression]",
            apply_operation(
                "replace",
                self.model,
                expression_input(search, STR),
                expression_input(replacement, STR),
            ),
        )

    def equals(self, value: str | ValueExpression[str]) -> "NullableExpression[bool, BoolExpression]":
        """Test this string for equality; a null value stays null.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            assert Row.name.expression.equals("Depot").model.operator == "equals"
            ```
        """
        return cast(
            "NullableExpression[bool, BoolExpression]",
            apply_operation("equals", self.model, expression_input(value, STR)),
        )

    def before_separator(
        self,
        separator: str,
        occurrence: int = 1,
        *,
        include_separator: bool = False,
    ) -> "NullableExpression[str, StrExpression]":
        """The text before the nth separator; absence is preserved.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            selected = Row.name.expression.before_separator("::")
            assert selected.model.operator == "before_separator"
            ```
        """
        if not separator:
            raise ValueError("separator must be non-empty")
        if occurrence < 1:
            raise ValueError("occurrence must be at least 1")
        return cast(
            "NullableExpression[str, StrExpression]",
            apply_operation(
                "before_separator",
                self.model,
                expression_input(separator, STR),
                occurrence=occurrence,
                include_separator=include_separator,
            ),
        )

    def after_separator(
        self,
        separator: str,
        occurrence: int = 1,
        *,
        include_separator: bool = False,
    ) -> "NullableExpression[str, StrExpression]":
        """The text after the nth separator; absence is preserved.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str | None] = field(name="name")

            selected = Row.name.expression.after_separator("::")
            assert selected.model.operator == "after_separator"
            ```
        """
        if not separator:
            raise ValueError("separator must be non-empty")
        if occurrence < 1:
            raise ValueError("occurrence must be at least 1")
        return cast(
            "NullableExpression[str, StrExpression]",
            apply_operation(
                "after_separator",
                self.model,
                expression_input(separator, STR),
                occurrence=occurrence,
                include_separator=include_separator,
            ),
        )




__all__ = ["NullableExpression"]
