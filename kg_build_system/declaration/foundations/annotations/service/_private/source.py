"""Render an annotation DTO back to inline authoring source."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ....source import SourceFragment
from ...model.internal.dto.blueprint_dto import AnnotationDTO

if TYPE_CHECKING:
    from ...service.internal.service.source import AnnotationSourceContext

IMPORTS = {
    "kg_build_system.topology": (
        "from kg_build_system.declaration.foundations.annotations import (",
        "    EdgeLabel, NodeLabel,",
        ")",
    ),
}


def render_value(value: Any) -> str:
    if isinstance(value, str):
        return repr(value)
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, Mapping):
        items = ", ".join(
            f"{key!r}: {render_value(item)}" for key, item in value.items()
        )
        return "{" + items + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(render_value(item) for item in value) + "]"
    return repr(value)


def class_name(dto: AnnotationDTO, context: AnnotationSourceContext) -> str:
    declared = context.class_names.get((dto.namespace, dto.id))
    if declared is not None:
        return declared
    if dto.namespace == "kg_build_system.topology" and dto.id == "node_label":
        return "NodeLabel"
    if dto.namespace == "kg_build_system.topology" and dto.id == "edge_label":
        return "EdgeLabel"
    return "".join(part.capitalize() for part in dto.id.split("_")) or "Annotation"


def imports(dto: AnnotationDTO) -> tuple[str, ...]:
    lines = IMPORTS.get(dto.namespace)
    return () if lines is None else ("\n".join(lines),)


def render_annotation_source(
    dto: AnnotationDTO, context: AnnotationSourceContext,
) -> SourceFragment:
    """Render one annotation DTO as an inline authoring expression."""
    name = class_name(dto, context)
    arguments = dto.arguments
    if (
        isinstance(arguments, Mapping)
        and set(arguments) == {"label"}
        and name in {"NodeLabel", "EdgeLabel"}
    ):
        text = f"{name}({render_value(arguments['label'])})"
    elif isinstance(arguments, Mapping) and arguments:
        values = ", ".join(
            f"{key}={render_value(value)}"
            for key, value in sorted(arguments.items())
        )
        text = f"{name}({values})"
    elif arguments is None:
        text = f"{name}()"
    else:
        text = f"{name}({render_value(arguments)})"
    return SourceFragment(text=text, imports=imports(dto))


__all__ = ["render_annotation_source"]
