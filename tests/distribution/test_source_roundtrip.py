"""Contract tests: layer and blueprint source round-trip."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kg_build_system.distribution.interpreter import GraphBlueprint, create_blueprint
from kg_build_system.distribution.interpreter.service.internal import (
    blueprint_to_document,
    blueprint_to_source,
)
from kg_build_system.distribution.languages.binding import node_binding
from kg_build_system.distribution.languages.binding.service.internal import BindingLanguage
from kg_build_system.distribution.languages.asset.service.internal import AssetLanguage
from kg_build_system.distribution.languages.data import Field, Table, field
from kg_build_system.distribution.languages.data.service.internal.adapters.kernel_language import DataLanguage
from kg_build_system.distribution.languages.topology import (
    Node,
    PropertySlot,
    property,
)
from kg_build_system.distribution.languages.topology.service.internal import TopologyLanguage
from .support import TestEstate


class SiteTable(Table[TestEstate]):
    site_id: Field[str] = field()


class SiteNode(Node):
    site_id: PropertySlot[str] = property()


def _fixture() -> GraphBlueprint:
    binding = node_binding(
        target=SiteNode,
        build_key=SiteTable.site_id,
        properties=SiteNode(site_id=SiteTable.site_id),
    )
    return create_blueprint(bindings=(binding,))


def _canonical(document: object) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def _source_from_layers(blueprint: GraphBlueprint) -> str:
    from kg_build_system.distribution.service.internal.rendering import class_name

    asset_class_names = {
        asset.name: class_name(asset.name, "Asset")
        for asset in blueprint.assets.assets
    }
    fragments = (
        AssetLanguage().render(blueprint.assets, None),
        TopologyLanguage().render(blueprint.graph, None),
        DataLanguage().render(
            blueprint.data, None, class_names=asset_class_names,
        ),
        BindingLanguage().render(blueprint.bindings, None),
    )
    imports = sorted({
        import_line
        for fragment in fragments
        for import_line in fragment.imports
    })
    bodies = [
        fragment.body.strip()
        for fragment in fragments
        if fragment.body.strip()
    ]
    parts = ["\n".join(imports)] if imports else []
    parts.extend(bodies)
    return "\n\n".join(parts) + "\n"


def _recreate(source: str) -> GraphBlueprint:
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory) / "graph_fixture"
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "graph.py").write_text(source)
        return create_blueprint(namespace_path=package)


class SourceRoundTripTests(unittest.TestCase):
    def test_the_layer_source_fragments_recreate_every_layer(self) -> None:
        first = _fixture()
        second = _recreate(_source_from_layers(first))

        original = blueprint_to_document(first)
        regenerated = blueprint_to_document(second)
        for layer in ("graph", "data", "bindings"):
            with self.subTest(layer=layer):
                self.assertEqual(
                    _canonical(original[layer]),
                    _canonical(regenerated[layer]),
                )

    def test_the_blueprint_source_recreates_the_blueprint(self) -> None:
        first = _fixture()
        second = _recreate(blueprint_to_source(first, None))

        self.assertEqual(
            _canonical(blueprint_to_document(first)),
            _canonical(blueprint_to_document(second)),
        )


if __name__ == "__main__":
    unittest.main()
