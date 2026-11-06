"""Render the graph declaration DTO as authoring source."""
from __future__ import annotations

from kg_build_system.distribution.languages.semantics.service.internal import (
    render_graph_semantics,
)
from kg_build_system.distribution.service.internal.rendering import class_name
from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.graph_dto import GraphDeclarationDTO


def _options_lines(
    value: GraphDeclarationDTO, imports: set[str],
) -> list[str]:
    imports.add("from kg_build_system import GraphOptions")
    indent = "        "
    lines = ["    options = GraphOptions(", f"{indent}name={value.name!r},"]
    if value.description is not None:
        lines.append(f"{indent}description={value.description!r},")
    semantics: SourceFragment = render_graph_semantics(value.semantics)
    imports.update(semantics.imports)
    semantics_lines = semantics.body.splitlines()
    semantics_lines[-1] = f"{semantics_lines[-1]},"
    lines.extend(f"{indent}{line}" for line in semantics_lines)
    lines.append("    )")
    return lines


def _class_source(
    value: GraphDeclarationDTO, imports: set[str],
) -> str:
    imports.add("from kg_build_system import Graph")
    own_name = class_name(value.name, "Graph")
    lines = [f"class {own_name}(Graph):"]
    lines.extend(_options_lines(value, imports))
    return "\n".join(lines)


def render_graph_declaration_source(
    value: GraphDeclarationDTO, context: object = None,
) -> SourceFragment:
    """Render a graph declaration DTO as deterministic authoring source.

    The ``semantics`` argument is rendered by the semantics language, so the
    graph language owns the class and option shape and nothing about the meaning
    units.

    Example:
        ```python
        from kg_build_system.distribution.languages.graph.service.internal import (
            render_graph_declaration_source,
        )

        fragment = render_graph_declaration_source(declaration)
        assert fragment.body.startswith("class ")
        ```
    """
    del context
    imports: set[str] = set()
    body = _class_source(value, imports) + "\n"
    return SourceFragment(
        kind="declaration", body=body, imports=tuple(sorted(imports)),
    )


__all__ = ["render_graph_declaration_source"]
