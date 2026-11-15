"""Render the meaning language values back to authoring source.

The renderer lives in the package's private zone; this module is the internal
entry point another layer composes.
"""
from __future__ import annotations

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.meaning_dto import MeaningDTO
from ...model.public.units import Meaning


def render_meaning_expression(value: Meaning | MeaningDTO) -> str:
    """Render only the ``Meaning(...)`` authoring expression.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning.model.public import (
            Claim, Meaning,
        )
        from kg_build_system.distribution.languages.meaning.service.internal import (
            render_meaning_expression,
        )

        expression = render_meaning_expression(
            Meaning(claims=(Claim("A claim."),)),
        )
        assert expression.startswith("Meaning(")
        ```
    """
    from .._private.source import (
        render_meaning_expression as render,
    )

    return render(value)


def render_meaning(value: Meaning | MeaningDTO) -> SourceFragment:
    """Render a declaration meaning value as an embeddable fragment.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning.model.public import (
            Claim, Meaning,
        )
        from kg_build_system.distribution.languages.meaning.service.internal import (
            render_meaning,
        )

        fragment = render_meaning(Meaning(claims=(Claim("A claim."),)))
        assert fragment.body.startswith("meaning=Meaning(")
        ```
    """
    from .._private.source import render_meaning as render

    return render(value)


__all__ = ["render_meaning", "render_meaning_expression"]
