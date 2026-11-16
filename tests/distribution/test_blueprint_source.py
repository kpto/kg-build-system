"""Contract test: blueprint -> authoring source -> blueprint.

The round trip is canonical: both blueprints produce the same document. The
test is skipped while the declaration language packages are being created.
"""
from __future__ import annotations

from kg_build_system import Meaning, Purpose
import json
import tempfile
import uuid
import unittest
from pathlib import Path

try:
    from kg_build_system.distribution.interpreter import (
        GraphBlueprint, create_blueprint,
    )
    from kg_build_system.distribution.interpreter.service.internal import (
        blueprint_to_document, blueprint_to_source,
    )
    from kg_build_system.distribution.languages.binding import node_binding
    from kg_build_system.distribution.languages.data import (
        Field, SourceRelation, field,
    )
    from kg_build_system.distribution.languages.topology import (
        Node, PropertySlot, property,
    )
except ImportError as error:  # pragma: no cover - concurrent refactor guard
    raise unittest.SkipTest(
        f"declaration blueprint dependencies are not available: {error}"
    ) from error

from .support import TestEstate
from kg_build_system import Omitted


class SiteSourceRelation(SourceRelation[TestEstate]):
    site_id: Field[str] = field(meaning=Omitted)


class SiteNode(Node):
    site_id: PropertySlot[str] = property(meaning=Omitted)


def _fixture() -> GraphBlueprint:
    binding = node_binding(
        target=SiteNode,
        rows=SiteSourceRelation.row_source(),
        bind=lambda row: __import__(
            "kg_build_system", fromlist=["NodeValues"]
        ).NodeValues(
            build_key=row.site_id.alter_rows().drop_null(),
            properties=SiteNode(site_id=row.site_id),
        ),
        meaning=Meaning(purpose=Purpose("Fulfil the fixture record from its rows.")),
    )
    return create_blueprint(bindings=(binding,))


def _canonical(blueprint: GraphBlueprint) -> str:
    return json.dumps(
        blueprint_to_document(blueprint), sort_keys=True, separators=(",", ":"),
    )


class BlueprintSourceTests(unittest.TestCase):
    def test_the_rendered_source_states_the_asset_and_generic_source_relation(self) -> None:
        source = blueprint_to_source(_fixture(), None)

        self.assertIn("class EstateAsset(Asset):", source)
        self.assertIn(
            "class SiteSourceRelation(SourceRelation[EstateAsset]):", source,
        )
        self.assertNotIn("bind_source", source)
        self.assertLess(
            source.index("class EstateAsset(Asset):"),
            source.index(
                "class SiteSourceRelation(SourceRelation[EstateAsset]):",
            ),
        )

    def test_the_rendered_source_recreates_the_blueprint(self) -> None:
        first = _fixture()
        source = blueprint_to_source(first, None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / f"graph_fixture_{uuid.uuid4().hex}"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "graph.py").write_text(source)
            second = create_blueprint(namespace_path=package)
        self.assertEqual(_canonical(first), _canonical(second))


if __name__ == "__main__":
    unittest.main()
