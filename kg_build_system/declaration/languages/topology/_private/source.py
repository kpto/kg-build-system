"""Render the topology blueprint DTO as authoring source."""
from __future__ import annotations

from typing import Any

from kg_build_system.declaration.foundations.annotations.internal import EdgeLabel, NodeLabel
from kg_build_system.declaration.foundations.annotations.internal import AnnotationDTO
from kg_build_system.declaration.internal import SourceFragment
from kg_build_system.declaration.internal.rendering import (
    class_name,
    member_name,
    render_annotation,
    render_docstring,
    render_logical_type,
)

from ..internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO, PropertyDTO,
)


def _options_source(
    kind: str,
    name: str,
    labels: tuple[str, ...],
    annotations: tuple[AnnotationDTO, ...],
    imports: set[str],
) -> tuple[str, ...]:
    option_class = "NodeOptions" if kind == "node" else "EdgeOptions"
    imports.add(f"from kg_build_system import {option_class}")
    label = NodeLabel if kind == "node" else EdgeLabel
    if labels:
        imports.add(f"from kg_build_system.declaration.foundations.annotations import {label.__name__}")
    rendered: list[str] = [f"{label.__name__}({value!r})" for value in labels]
    for annotation in annotations:
        if (
            annotation.namespace == label.namespace
            and annotation.id == label.annotation_id
        ):
            # The blueprint carries labels in their own field; a decoded
            # document may repeat one in the annotation list.
            continue
        rendered.append(render_annotation(annotation, imports))
    lines = [f"    options = {option_class}(", f"        name={name!r},"]
    if rendered:
        lines.append("        annotations=(")
        lines.extend(f"            {item}," for item in rendered)
        lines.append("        ),")
    lines.append("    )")
    return tuple(lines)


def _property_source(value: PropertyDTO, imports: set[str]) -> list[str]:
    attribute = member_name(value.name)
    type_source = render_logical_type(value.logical_type, imports)
    has_name = attribute != value.name
    has_annotations = bool(value.annotations)
    if not has_name and not has_annotations:
        lines = [f"    {attribute}: PropertySlot[{type_source}] = property()"]
    else:
        lines = [f"    {attribute}: PropertySlot[{type_source}] = property("]
        if has_name:
            lines.append(f"        name={value.name!r},")
        if has_annotations:
            lines.append("        annotations=(")
            lines.extend(
                f"            {render_annotation(item, imports)},"
                for item in value.annotations
            )
            lines.append("        ),")
        lines.append("    )")
    lines.extend(render_docstring(value.description))
    return lines


def _class_source(
    value: NodeDTO | EdgeDTO,
    *,
    node_classes: dict[str, str],
    edge_classes: dict[str, str],
) -> tuple[tuple[str, ...], set[str]]:
    imports: set[str] = set()
    kind = "node" if isinstance(value, NodeDTO) else "edge"
    suffix = "Node" if kind == "node" else "Edge"
    tier_base = (
        "AbstractNode" if value.abstract
        else "Node"
    ) if kind == "node" else (
        "AbstractEdge" if value.abstract else "Edge"
    )
    own_name = class_name(
        value.name, f"Abstract{suffix}" if value.abstract else suffix,
    )
    imports.add(f"from kg_build_system import {tier_base}")
    if value.properties:
        imports.add("from kg_build_system import PropertySlot")
        imports.add("from kg_build_system import property")

    bases: list[str] = []
    if value.parent is not None:
        parent_map = node_classes if kind == "node" else edge_classes
        parent_name = parent_map.get(value.parent)
        if parent_name is not None:
            bases.append(parent_name)
    if isinstance(value, EdgeDTO):
        source_name = node_classes.get(value.source, class_name(value.source, "Node"))
        target_name = node_classes.get(value.target, class_name(value.target, "Node"))
        bases.append(f"{tier_base}[{source_name}, {target_name}]")
    else:
        bases.append(tier_base)

    lines = [f"class {own_name}({', '.join(bases)}):"]
    lines.extend(render_docstring(value.description))
    if value.description:
        lines.append("")
    lines.extend(_options_source(
        kind, value.name, value.labels, value.annotations, imports,
    ))
    if value.properties:
        lines.append("")
        for index, item in enumerate(value.properties):
            if index:
                lines.append("")
            lines.extend(_property_source(item, imports))
    return tuple(lines), imports


def _depths(
    values: tuple[NodeDTO, ...] | tuple[EdgeDTO, ...],
) -> dict[str, int]:
    by_name = {item.name: item for item in values}
    result: dict[str, int] = {}

    def depth(name: str, seen: frozenset[str]) -> int:
        if name in result:
            return result[name]
        if name in seen:
            raise ValueError(f"topology parent cycle includes {name!r}")
        item = by_name[name]
        value = 0 if item.parent is None else 1 + depth(item.parent, seen | {name})
        result[name] = value
        return value

    for item in values:
        depth(item.name, frozenset())
    return result


def render_graph_source(part: GraphPartDTO, context: Any) -> SourceFragment:
    """Render a topology DTO as authoring source.

    The fragment declares one class per component, parents before children.
    Properties, labels and annotations use the shared type and annotation
    renderers, and every graph name is written explicitly in ``options``.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.dto import (
            GraphPartDTO, NodeDTO,
        )
        from kg_build_system.declaration.languages.topology.internal.service import (
            render_graph_source,
        )

        fragment = render_graph_source(
            GraphPartDTO(nodes=(NodeDTO("site"),)), None,
        )
        ```
    """
    node_classes = {
        item.name: class_name(
            item.name, "AbstractNode" if item.abstract else "Node",
        )
        for item in part.nodes
    }
    edge_classes = {
        item.name: class_name(
            item.name, "AbstractEdge" if item.abstract else "Edge",
        )
        for item in part.edges
    }
    imports: set[str] = set()
    node_depth = _depths(part.nodes)
    edge_depth = _depths(part.edges)
    chunks: list[str] = []
    for node in sorted(part.nodes, key=lambda item: (node_depth[item.name], item.name)):
        lines, needed = _class_source(
            node, node_classes=node_classes, edge_classes=edge_classes,
        )
        imports.update(needed)
        chunks.append("\n".join(lines))
    for edge in sorted(part.edges, key=lambda item: (edge_depth[item.name], item.name)):
        lines, needed = _class_source(
            edge, node_classes=node_classes, edge_classes=edge_classes,
        )
        imports.update(needed)
        chunks.append("\n".join(lines))
    body = "\n\n\n".join(chunks)
    if body:
        body += "\n"
    return SourceFragment(kind="declaration", body=body, imports=tuple(sorted(imports)))


__all__ = ["render_graph_source"]
