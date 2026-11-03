"""Render an annotation DTO back to inline authoring source."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from kg_build_system.kernel import SourceFragment
from ....model.internal.dto.blueprint_dto import AnnotationDTO


@dataclass(frozen=True, slots=True)
class AnnotationSourceContext:
    """Names the authoring classes used to render annotation DTOs.

    ``class_names`` is keyed by ``(namespace, id)``. Without an entry the
    renderer falls back to the payload's own id and emits a keyword call.
    """

    class_names: Mapping[tuple[str, str], str] = field(default_factory=dict)


def render_annotation_source(
    dto: AnnotationDTO, context: AnnotationSourceContext,
) -> SourceFragment:
    """Render one annotation DTO as an inline authoring expression.

    The label annotations render as ``NodeLabel("...")`` or
    ``EdgeLabel("...")``. Other annotations render as a keyword call to the
    class named by ``context``.

    Example:
        ```python
        from kg_build_system.distribution.languages.annotations.service.internal import (
            AnnotationDTO, render_annotation_source,
        )
        from kg_build_system.distribution.languages.annotations.service.internal.service import (
            AnnotationSourceContext,
        )

        fragment = render_annotation_source(
            AnnotationDTO("kg_build_system.topology", "node_label", {"label": "Sensor"}),
            AnnotationSourceContext(),
        )
        assert fragment.body == 'NodeLabel("Sensor")'
        ```
    """
    from ..._private.source import render_annotation_source as render

    return render(dto, context)


__all__ = ["AnnotationSourceContext", "render_annotation_source"]
