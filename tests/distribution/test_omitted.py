from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetOptions,
    AssetProfile,
    Claim,
    EdgeOptions,
    EdgeOptionsTemplate,
    Field,
    GraphOptions,
    Meaning,
    Node,
    NodeOptions,
    NodeOptionsTemplate,
    Omitted,
    PropertySlot,
    SourceRelation,
    SourceRelationOptions,
    StructOptions,
    field,
    is_omitted,
    property,
)
from kg_build_system import create_blueprint
from kg_build_system.distribution.languages.topology.service.internal import (
    render_graph_source,
)


def _profile() -> AssetProfile:
    return AssetProfile(
        subject="fixture",
        coverage="one fixture",
        authority=AssetAuthority.INFERRED,
        basis="the Omitted test",
    )


class OmittedApiTests(unittest.TestCase):
    def test_the_marker_is_explicit(self) -> None:
        self.assertTrue(is_omitted(Omitted))
        self.assertFalse(is_omitted(None))
        self.assertFalse(is_omitted(Meaning(claims=(Claim("A claim."),))))

    def test_a_field_requires_a_meaning_or_the_marker(self) -> None:
        with self.assertRaises(TypeError):
            field(name="site_id")  # type: ignore[call-arg]

        declared = field(name="site_id", meaning=Omitted)
        self.assertTrue(is_omitted(declared.metadata.meaning))

    def test_struct_options_require_a_meaning_or_the_marker(self) -> None:
        with self.assertRaises(TypeError):
            StructOptions()  # type: ignore[call-arg]
        self.assertTrue(is_omitted(StructOptions(meaning=Omitted).meaning))

    def test_source_relation_options_require_a_contract_or_the_marker(self) -> None:
        with self.assertRaises(TypeError):
            SourceRelationOptions()  # type: ignore[call-arg]
        self.assertTrue(
            is_omitted(SourceRelationOptions(contract=Omitted).contract)
        )

    def test_node_and_edge_options_require_a_meaning_or_the_marker(self) -> None:
        with self.assertRaises(TypeError):
            NodeOptions()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            EdgeOptions()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            NodeOptionsTemplate()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            EdgeOptionsTemplate()  # type: ignore[call-arg]

        for options in (
            NodeOptions(meaning=Omitted),
            EdgeOptions(meaning=Omitted),
            NodeOptionsTemplate(meaning=Omitted),
            EdgeOptionsTemplate(meaning=Omitted),
        ):
            self.assertIsNone(options.meaning)

    def test_a_graph_cannot_opt_out(self) -> None:
        with self.assertRaises(TypeError):
            GraphOptions(meaning=Omitted)  # type: ignore[arg-type]

    def test_a_property_requires_a_meaning_or_the_marker(self) -> None:
        with self.assertRaises(TypeError):
            property()  # type: ignore[call-arg]

    def test_the_blueprint_records_no_meaning_for_an_omission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "omitted_project"
            root.mkdir()
            (root / "__init__.py").write_text("")
            (root / "graph.py").write_text(
                "from kg_build_system import (\n"
                "    Asset, AssetAuthority, AssetOptions, AssetProfile, Field,\n"
                "    Node, NodeOptions, Omitted, PropertySlot, SourceRelation,\n"
                "    SourceRelationOptions, field, property,\n"
                ")\n\n\n"
                "class Estate(Asset):\n"
                "    options = AssetOptions(\n"
                "        profile=AssetProfile(\n"
                "            subject='fixture',\n"
                "            coverage='one fixture',\n"
                "            authority=AssetAuthority.INFERRED,\n"
                "            basis='the Omitted test',\n"
                "        ),\n"
                "        meaning=Omitted,\n"
                "    )\n\n\n"
                "class Row(SourceRelation[Estate]):\n"
                "    options = SourceRelationOptions(name='rows', contract=Omitted)\n"
                "    site_id: Field[str] = field(name='site_id', meaning=Omitted)\n\n\n"
                "class Site(Node):\n"
                "    options = NodeOptions(name='site', meaning=Omitted)\n"
                "    site_id: PropertySlot[str] = property(meaning=Omitted)\n"
            )
            blueprint = create_blueprint(namespace_path=root)

        self.assertIsNone(blueprint.assets.assets[0].meaning)
        self.assertIsNone(blueprint.data.source_relations[0].meaning)
        self.assertIsNone(blueprint.graph.nodes[0].meaning)

        fragment = render_graph_source(blueprint.graph, None)
        self.assertIn("meaning=Omitted", fragment.body)


if __name__ == "__main__":
    unittest.main()
