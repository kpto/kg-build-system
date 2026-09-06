"""Typed text expression family."""
from __future__ import annotations

from ..types import BOOL, STR
from ._coercion import expression_input
from .base import operation
from .boolean import BoolExpression
from .values import ValueExpression


class StrExpression(ValueExpression[str]):
    def __init__(self, expression):
        if expression.logical_type != STR:
            raise TypeError("StrExpression requires the str logical type")
        super().__init__(expression)

    def prepend(self, value: str | ValueExpression[str]) -> "StrExpression":
        return StrExpression(
            operation("concat", expression_input(value, STR), self.model, logical_type=STR)
        )

    def append(self, value: str | ValueExpression[str]) -> "StrExpression":
        return StrExpression(
            operation("concat", self.model, expression_input(value, STR), logical_type=STR)
        )

    def equals(self, value: str | ValueExpression[str]) -> "BoolExpression":
        """Test this string for equality, producing a Boolean row predicate."""
        return BoolExpression(
            operation(
                "equals", self.model, expression_input(value, STR), logical_type=BOOL,
            )
        )

    def split_before(self, separator: str) -> "StrExpression":
        """The text before the first ``separator``; the whole string without one.

        The identifier-pair reader of this vocabulary: a source that ships
        ``Reactome:R-HSA-70635`` as one string can name the database half here
        and the reference half with :meth:`split_after`.
        """
        return StrExpression(
            operation(
                "split_before", self.model, expression_input(separator, STR),
                logical_type=STR,
            )
        )

    def split_after(self, separator: str) -> "StrExpression":
        """The text after the first ``separator``, later separators included.

        ``Wikipedia:Neural_development#Neuron_migration`` split on ``:``
        yields the full page title, not only up to the next separator.
        """
        return StrExpression(
            operation(
                "split_after", self.model, expression_input(separator, STR),
                logical_type=STR,
            )
        )

    def replaced(self, search: str, replacement: str) -> "StrExpression":
        """Replace every occurrence of ``search`` with ``replacement``.

        The identity-space normalizer of this vocabulary: sources that spell
        an identifier one way (a CURIE's ``HP:0000118``) can name the record
        another space holds (``HP_0000118``) without inventing a bespoke
        operation per pair.
        """
        return StrExpression(
            operation(
                "replaced", self.model,
                expression_input(search, STR), expression_input(replacement, STR),
                logical_type=STR,
            )
        )


__all__ = ["StrExpression"]
