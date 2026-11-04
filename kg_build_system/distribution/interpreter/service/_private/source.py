"""Render a blueprint back to authoring source.

The blueprint does not know how a layer is written. It asks the asset, data,
topology and binding renderers for their fragments and joins those fragments in
a stable order.
"""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.asset.service.internal import AssetLanguage
from kg_build_system.distribution.languages.binding.service.internal import BindingLanguage
from kg_build_system.distribution.languages.data.service.internal import DataLanguage
from kg_build_system.distribution.languages.topology.service.internal import TopologyLanguage
from kg_build_system.distribution.service.internal.rendering import class_name
from ...model.public import GraphBlueprint


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
    concatenation of the asset, topology, data and binding fragments, which is
    the inverse of :func:`create_blueprint`.
    """
    asset_class_names = {
        asset.name: class_name(asset.name, "Asset")
        for asset in blueprint.assets.assets
    }
    return _assemble((
        AssetLanguage().render(blueprint.assets, context),
        TopologyLanguage().render(blueprint.graph, context),
        DataLanguage().render(
            blueprint.data, context, class_names=asset_class_names,
        ),
        BindingLanguage().render(blueprint.bindings, context),
    ))


__all__ = ["blueprint_to_source"]
