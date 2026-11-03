"""Render expression DTOs back to inline authoring source."""
from __future__ import annotations

from kg_build_system.kernel import SourceFragment
from ...model.internal.dto.blueprint_dto import ExpressionDTO


def render_expression_source(dto: ExpressionDTO) -> SourceFragment:
    """Render one expression DTO as an inline authoring expression.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.distribution.languages.expressions.service.internal import (
            render_expression_source,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        node = LiteralExpressionDTO(logical_type=UnitTypeDTO("int"), value=1)
        assert render_expression_source(node).body.startswith("value_expression(")
        ```
    """
    from .._private.source import render_expression_source as render

    return render(dto)


__all__ = ["render_expression_source"]
