"""Collection-cardinality expression constructors."""
from typing import Any, overload

from .core import Expression, ValueRef, item_type
from .inputs import to_expression


class CollectionExpressions:
    @overload
    def expand[E](self, value: ValueRef[list[E]] | Expression[list[E]]) -> Expression[E]: ...

    @overload
    def expand[T](self, value: Expression[T] | ValueRef[T]) -> Expression[T]: ...

    def expand(self, value: Any) -> Expression[Any]:
        expression = to_expression(value)
        element = item_type(expression.type_hint)
        if element is None and expression.cardinality != "collection":
            raise TypeError("expand requires a declared list[T] value")
        return Expression("expand", (expression,), element or expression.type_hint, "expanded")


collection = CollectionExpressions()
