"""Author-facing Boolean predicate combinators."""
from __future__ import annotations

from ...model.public.selection import Selection
from ..internal.boolean import all_of as all_of_impl
from ..internal.boolean import any_of as any_of_impl


def all_of(*predicates: Selection[bool]) -> Selection[bool]:
    """Combine predicates with logical and.

    Example:
        ```python
        from kg_build_system import all_of, value_expression

        both = all_of(value_expression(True), value_expression(False))
        assert both.logical_type.name == "bool"
        ```
    """
    from ..internal.selections import as_expression, select_expression

    expressions = tuple(as_expression(item) for item in predicates)
    return select_expression(all_of_impl(*expressions))


def any_of(*predicates: Selection[bool]) -> Selection[bool]:
    """Combine predicates with logical or.

    Example:
        ```python
        from kg_build_system import any_of, value_expression

        either = any_of(value_expression(False), value_expression(True))
        assert either.logical_type.name == "bool"
        ```
    """
    from ..internal.selections import as_expression, select_expression

    expressions = tuple(as_expression(item) for item in predicates)
    return select_expression(any_of_impl(*expressions))


__all__ = ["all_of", "any_of"]
