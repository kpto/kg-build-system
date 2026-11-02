"""Typed text expression family."""
from __future__ import annotations

from ..types.interfaces import BOOL, STR
from ._apply import apply_operation
from ._coercion import expression_input
from .boolean import BoolExpression
from .values import ValueExpression


class StrExpression(ValueExpression[str]):
    def __init__(self, expression):
        if expression.logical_type != STR:
            raise TypeError("StrExpression requires the str logical type")
        super().__init__(expression)

    def prepend(self, value: str | ValueExpression[str]) -> "StrExpression":
        return StrExpression(
            apply_operation("concat", expression_input(value, STR), self.model, result_type=STR).model
        )

    def append(self, value: str | ValueExpression[str]) -> "StrExpression":
        return StrExpression(
            apply_operation("concat", self.model, expression_input(value, STR), result_type=STR).model
        )

    def equals(self, value: str | ValueExpression[str]) -> "BoolExpression":
        """Test this string for equality, producing a Boolean row predicate."""
        return BoolExpression(
            apply_operation("equals", self.model, expression_input(value, STR)).model
        )

    def replace(self, search: str, replacement: str) -> "StrExpression":
        """Replace every occurrence of ``search`` with ``replacement``."""
        return StrExpression(
            apply_operation(
                "replace",
                self.model,
                expression_input(search, STR),
                expression_input(replacement, STR),
            ).model
        )

    def _separator_cut(
        self,
        separator: str,
        occurrence: int,
        side: str,
        *,
        include_separator: bool,
    ) -> "StrExpression":
        if not separator:
            raise ValueError("separator must be non-empty")
        if occurrence < 1:
            raise ValueError("occurrence must be at least 1")
        operator = {
            "before": "before_separator",
            "after": "after_separator",
        }[side]
        return StrExpression(
            apply_operation(
                operator,
                self.model,
                expression_input(separator, STR),
                occurrence=occurrence,
                include_separator=include_separator,
            ).model
        )

    def before_separator(
        self,
        separator: str,
        occurrence: int = 1,
        *,
        include_separator: bool = False,
    ) -> "StrExpression":
        """The text before the nth appearance of ``separator``.

        The separator at the cut is excluded by default. The whole string when
        the separator does not appear that many times.
        """
        return self._separator_cut(
            separator,
            occurrence,
            "before",
            include_separator=include_separator,
        )

    def after_separator(
        self,
        separator: str,
        occurrence: int = 1,
        *,
        include_separator: bool = False,
    ) -> "StrExpression":
        """The text after the nth appearance of ``separator``.

        The separator at the cut is excluded by default; later separators stay
        in the result. The empty string when the separator does not appear that
        many times.
        """
        return self._separator_cut(
            separator,
            occurrence,
            "after",
            include_separator=include_separator,
        )


__all__ = ["StrExpression"]
