"""Render the graph declaration DTO as authoring source."""
from __future__ import annotations

from kg_build_system.distribution.languages.meaning.service.internal import (
    render_meaning,
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
    meaning: SourceFragment = render_meaning(value.meaning)
    imports.update(meaning.imports)
    meaning_lines = meaning.body.splitlines()
    meaning_lines[-1] = f"{meaning_lines[-1]},"
    lines.extend(f"{indent}{line}" for line in meaning_lines)
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

    The ``meaning`` argument is rendered by the meaning language, so the
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
