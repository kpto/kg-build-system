"""Graph-property binding boundary."""
from ..expressions import ExpressionInput, to_expression
from .models import ExpressionBinding


def bind[T](value: ExpressionInput[T]) -> ExpressionBinding[T]:
    """Bind a portable value expression to a graph property slot."""
    return ExpressionBinding(expression=to_expression(value))
