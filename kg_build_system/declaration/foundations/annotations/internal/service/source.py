"""Render an annotation DTO back to inline authoring source."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ....source import SourceFragment
from ..dto.blueprint_dto import AnnotationDTO

_IMPORTS = {
    "kg_build_system.topology": (
        "from kg_build_system.declaration.foundations.annotations import (",
        "    EdgeLabel, NodeLabel,",
        ")",
    ),
}


@dataclass(frozen=True, slots=True)
class AnnotationSourceContext:
    """Names the authoring classes used to render annotation DTOs.

    ``class_names`` is keyed by ``(namespace, id)``. Without an entry the
    renderer falls back to the payload's own id and emits a keyword call.
    """

    class_names: Mapping[tuple[str, str], str] = field(default_factory=dict)


def _render_value(value: Any) -> str:
    if isinstance(value, str):
        return repr(value)
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, Mapping):
        items = ", ".join(
            f"{key!r}: {_render_value(item)}" for key, item in value.items()
        )
        return "{" + items + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    return repr(value)


def _class_name(dto: AnnotationDTO, context: AnnotationSourceContext) -> str:
    declared = context.class_names.get((dto.namespace, dto.id))
    if declared is not None:
        return declared
    if dto.namespace == "kg_build_system.topology" and dto.id == "node_label":
        return "NodeLabel"
    if dto.namespace == "kg_build_system.topology" and dto.id == "edge_label":
        return "EdgeLabel"
    return "".join(part.capitalize() for part in dto.id.split("_")) or "Annotation"


def _imports(dto: AnnotationDTO) -> tuple[str, ...]:
    lines = _IMPORTS.get(dto.namespace)
    return () if lines is None else ("\n".join(lines),)


def render_annotation_source(
    dto: AnnotationDTO, context: AnnotationSourceContext,
) -> SourceFragment:
    """Render one annotation DTO as an inline authoring expression.

    The label annotations render as ``NodeLabel("...")`` or
    ``EdgeLabel("...")``. Other annotations render as a keyword call to the
    class named by ``context``.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations.internal import (
            AnnotationDTO, render_annotation_source,
        )
        from kg_build_system.declaration.foundations.annotations.internal.service import (
            AnnotationSourceContext,
        )

        fragment = render_annotation_source(
            AnnotationDTO("kg_build_system.topology", "node_label", {"label": "Sensor"}),
            AnnotationSourceContext(),
        )
        assert fragment.text == 'NodeLabel("Sensor")'
        ```
    """
    name = _class_name(dto, context)
    arguments = dto.arguments
    if (
        isinstance(arguments, Mapping)
        and set(arguments) == {"label"}
        and name in {"NodeLabel", "EdgeLabel"}
    ):
        text = f"{name}({_render_value(arguments['label'])})"
    elif isinstance(arguments, Mapping) and arguments:
        values = ", ".join(
            f"{key}={_render_value(value)}"
            for key, value in sorted(arguments.items())
        )
        text = f"{name}({values})"
    elif arguments is None:
        text = f"{name}()"
    else:
        text = f"{name}({_render_value(arguments)})"
    return SourceFragment(text=text, imports=_imports(dto))


__all__ = ["AnnotationSourceContext", "render_annotation_source"]
