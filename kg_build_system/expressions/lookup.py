"""Lookup expression constructors."""
from typing import Any

from ..data_types import validate_value_type
from .core import Expression, PermittedExpressionValue
from .inputs import ExpressionInput, to_expression


class LookupExpressions:
    def one[K: PermittedExpressionValue, T: PermittedExpressionValue](self, *, key: ExpressionInput[K], match: ExpressionInput[K], value: ExpressionInput[T], as_type: type[T]) -> Expression[T]:
        validate_value_type(as_type, context="lookup result", allow_collection=True)
        return Expression("lookup_one", (to_expression(key), to_expression(match), to_expression(value)), as_type)


lookup = LookupExpressions()
