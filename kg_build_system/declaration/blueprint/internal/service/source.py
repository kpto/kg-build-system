"""Render a blueprint back to authoring source.

The blueprint does not know how a layer is written. It asks the table, topology
and binding renderers for their fragments and joins those fragments in a stable
order.
"""
from __future__ import annotations

from typing import Any

from ....languages.binding.internal import BindingLanguage
from ....languages.table.internal import TableLanguage
from ....languages.topology.internal import TopologyLanguage
from ...public.dto.graph_blueprint import GraphBlueprint


def _fragment_text(fragment: Any) -> str:
    if isinstance(fragment, str):
        return fragment
    for attribute in ("body", "text", "source", "code"):
        value = getattr(fragment, attribute, None)
        if isinstance(value, str):
            return value
    return str(fragment)


def _import_line(value: Any) -> str:
    text = str(value)
    if text.startswith(("import ", "from ")):
        return text
    return f"import {text}"


def _assemble(fragments: tuple[Any, ...]) -> str:
    imports: set[str] = set()
    bodies: list[str] = []
    for fragment in fragments:
        imports.update(
            _import_line(value) for value in getattr(fragment, "imports", ())
        )
        text = _fragment_text(fragment).strip()
        if text:
            bodies.append(text)
    parts = ["\n".join(sorted(imports))] if imports else []
    parts.extend(bodies)
    return "\n\n".join(parts) + ("\n" if parts else "")


def blueprint_to_source(blueprint: GraphBlueprint, context: Any) -> str:
    """Render a blueprint as authoring source.

    ``context`` is passed unchanged to each layer renderer. The result is the
    concatenation of the topology, data and binding fragments, which is the
    inverse of :func:`create_blueprint`.

    Example:
    ```python
    from kg_build_system.declaration.blueprint.internal import blueprint_to_source

    source = blueprint_to_source(blueprint, context)
    ```
    """
    return _assemble((
        TopologyLanguage().render(blueprint.graph, context),
        TableLanguage().render(blueprint.data, context),
        BindingLanguage().render(blueprint.bindings, context),
    ))


__all__ = ["blueprint_to_source"]
