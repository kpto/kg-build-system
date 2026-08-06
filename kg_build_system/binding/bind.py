"""Graph-property binding boundary."""
from typing import cast

from ..expressions import Expression, ExpressionInput, to_expression
from ..topology.models import GraphValue
from .models import ExpressionBinding


def bind[T: GraphValue](value: ExpressionInput[T]) -> ExpressionBinding[T]:
    """Bind a portable value expression to a graph property slot."""
    # ``ExpressionInput`` is a union; pyright cannot preserve its shared ``T``
    # through the normalisation overload, although the public signature does.
    return ExpressionBinding(expression=cast(Expression[T], to_expression(value)))
