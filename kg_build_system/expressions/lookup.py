"""Lookup expression constructors."""
from typing import Any

from .core import Expression
from .inputs import to_expression


class LookupExpressions:
    def one[T](self, *, key: Any, match: Any, value: Any, as_type: type[T]) -> Expression[T]:
        return Expression("lookup_one", (to_expression(key), to_expression(match), to_expression(value)), as_type)


lookup = LookupExpressions()
