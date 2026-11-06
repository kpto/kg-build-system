"""Render the semantics language values back to authoring source.

The renderer lives in the package's private zone; this module is the internal
entry point another layer composes.
"""
from __future__ import annotations

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.semantics_dto import GraphSemanticsDTO, SemanticsDTO
from ...model.public.units import GraphSemantics, Semantics


def render_semantics_expression(value: Semantics | SemanticsDTO) -> str:
    """Render only the ``Semantics(...)`` authoring expression.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.model.public import (
            Claim, Semantics,
        )
        from kg_build_system.distribution.languages.semantics.service.internal import (
            render_semantics_expression,
        )

        expression = render_semantics_expression(
            Semantics(claims=(Claim("A claim."),)),
        )
        assert expression.startswith("Semantics(")
        ```
    """
    from .._private.source import (
        render_semantics_expression as render,
    )

    return render(value)


def render_semantics(value: Semantics | SemanticsDTO) -> SourceFragment:
    """Render a declaration semantics value as an embeddable fragment.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.model.public import (
            Claim, Semantics,
        )
        from kg_build_system.distribution.languages.semantics.service.internal import (
            render_semantics,
        )

        fragment = render_semantics(Semantics(claims=(Claim("A claim."),)))
        assert fragment.body.startswith("semantics=Semantics(")
        ```
    """
    from .._private.source import render_semantics as render

    return render(value)


def render_graph_semantics(
    value: GraphSemantics | GraphSemanticsDTO,
) -> SourceFragment:
    """Render a graph semantics value as an embeddable fragment.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.model.public import (
            GraphSemantics, Purpose,
        )
        from kg_build_system.distribution.languages.semantics.service.internal import (
            render_graph_semantics,
        )

        fragment = render_graph_semantics(
            GraphSemantics(purpose=Purpose("A purpose.")),
        )
        assert fragment.body.startswith("semantics=GraphSemantics(")
        ```
    """
    from .._private.source import render_graph_semantics as render

    return render(value)


__all__ = [
    "render_graph_semantics", "render_semantics",
    "render_semantics_expression",
]
