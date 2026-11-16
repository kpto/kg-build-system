"""Contract tests for the graph declaration in the blueprint.

The blueprint carries an optional project-level graph declaration. These tests
guard the field, assembly, document codec, source rendering and purpose
validation. They skip only while the concurrent graph and meaning language
packages are unavailable.
"""
from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

try:
    from kg_build_system.distribution.interpreter import (
        GraphBlueprint, create_blueprint,
    )
    from kg_build_system.distribution.interpreter.service.internal import (
        assemble_blueprint, blueprint_from_document, blueprint_to_document,
        blueprint_to_source, validate_blueprint,
    )
    from kg_build_system.distribution.interpreter.service.internal.link import (
        link_blueprint,
    )
    from kg_build_system.distribution.languages.asset.model.internal import (
        AssetPartDTO,
    )
    from kg_build_system.distribution.languages.asset.service.internal import (
        AssetLanguage,
    )
    from kg_build_system.distribution.languages.binding.service.internal import (
        BindingLanguage,
    )
    from kg_build_system.distribution.languages.data.model.internal import (
        DataPartDTO,
    )
    from kg_build_system.distribution.languages.data.service.internal import (
        DataLanguage,
    )
    from kg_build_system.distribution.languages.expressions.service.internal import (
        ExpressionsLanguage,
    )
    from kg_build_system.distribution.languages.graph.model.internal.dto import (
        GraphDeclarationDTO,
    )
    from kg_build_system.distribution.languages.graph.model.public import (
        Graph,
        GraphOptions,
    )
    from kg_build_system.distribution.languages.graph.service.internal import (
        GraphLanguage,
    )
    from kg_build_system.distribution.languages.meaning.model.internal import (
        ClaimDTO,
        LimitationDTO,
        PurposeDTO,
        MeaningDTO,
    )
    from kg_build_system.distribution.languages.meaning.model.public import (
        Claim,
        Limitation,
        Purpose,
        Meaning,
    )
    from kg_build_system.distribution.languages.topology.model.internal import (
        GraphPartDTO, NodeDTO,
    )
    from kg_build_system.distribution.languages.topology.service.internal import (
        TopologyLanguage,
    )
except ImportError as error:  # pragma: no cover - concurrent package guard
    raise unittest.SkipTest(
        f"graph blueprint dependencies are not available: {error}"
    ) from error


def _meaning() -> MeaningDTO:
    return MeaningDTO(
        purpose=PurposeDTO(
            text="Prioritise targets for disease evidence review.",
            limitations=(
                LimitationDTO("Uncurated literature is out of scope."),
            ),
        ),
        claims=(ClaimDTO("The graph is a curated target-disease model."),),
    )


def _declaration() -> GraphDeclarationDTO:
    return GraphDeclarationDTO(
        name="open_targets",
        meaning=_meaning(),
    )


class _Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self) -> tuple[object, ...]:
        return self._values


class FixtureGraph(Graph):
    options = GraphOptions(
        name="fixture",
        meaning=Meaning(
            purpose=Purpose("Exercise the interpreter."),
            claims=(Claim("The fixture graph describes one thing."),),
        ),
    )


def _languages() -> tuple[object, ...]:
    return (
        ExpressionsLanguage(), AssetLanguage(), DataLanguage(),
        TopologyLanguage(), BindingLanguage(), GraphLanguage(),
    )


def _empty_blueprint(
    declaration: GraphDeclarationDTO | None = None,
) -> GraphBlueprint:
    return GraphBlueprint(
        graph=GraphPartDTO(),
        data=DataPartDTO(structs=(), source_relations=(), derived_relations=()),
        assets=AssetPartDTO(),
        bindings=(),
        graph_declaration=declaration,
    )


class GraphBlueprintLinkerTests(unittest.TestCase):
    def test_default_roots_include_the_graph_declaration(self) -> None:
        blueprint = link_blueprint(_languages(), _Namespace(FixtureGraph))

        self.assertIsNotNone(blueprint.graph_declaration)
        assert blueprint.graph_declaration is not None
        self.assertEqual(blueprint.graph_declaration.name, "fixture")

    def test_narrow_roots_do_not_add_the_graph_declaration(self) -> None:
        blueprint = link_blueprint(
            _languages(), _Namespace(FixtureGraph), roots=("binding",),
        )

        self.assertIsNone(blueprint.graph_declaration)


class GraphBlueprintCodecTests(unittest.TestCase):
    def test_a_blueprint_without_a_graph_declaration_round_trips(self) -> None:
        blueprint = _empty_blueprint()
        document = blueprint_to_document(blueprint)

        self.assertNotIn("graph_declaration", document)
        self.assertEqual(blueprint_from_document(document), blueprint)

    def test_a_graph_declaration_round_trips_through_assembly(self) -> None:
        declaration = _declaration()
        blueprint = assemble_blueprint(
            GraphPartDTO(),
            DataPartDTO(structs=(), source_relations=(), derived_relations=()),
            AssetPartDTO(),
            (),
            graph_declaration=declaration,
        )

        self.assertIs(blueprint.graph_declaration, declaration)

    def test_a_graph_declaration_round_trips_through_the_codec(self) -> None:
        blueprint = _empty_blueprint(_declaration())
        document = blueprint_to_document(blueprint)

        self.assertIn("graph_declaration", document)
        self.assertEqual(
            blueprint_from_document(document).graph_declaration,
            _declaration(),
        )


class GraphBlueprintSourceTests(unittest.TestCase):
    def test_source_renders_the_graph_declaration_first(self) -> None:
        blueprint = GraphBlueprint(
            graph=GraphPartDTO(nodes=(NodeDTO("site"),)),
            data=DataPartDTO(structs=(), source_relations=(), derived_relations=()),
            assets=AssetPartDTO(),
            bindings=(),
            graph_declaration=_declaration(),
        )

        source = blueprint_to_source(blueprint, None)

        self.assertIn("class OpenTargetsGraph(Graph):", source)
        self.assertIn("meaning=Meaning(", source)
        self.assertTrue(source.startswith("from kg_build_system import"))
        self.assertLess(
            source.index("class OpenTargetsGraph(Graph):"),
            source.index("class SiteNode(Node):"),
        )

    def test_source_round_trip_preserves_graph_meaning(self) -> None:
        first = _empty_blueprint(_declaration())
        source = blueprint_to_source(first, None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / f"graph_fixture_{uuid.uuid4().hex}"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "graph.py").write_text(source)
            second = create_blueprint(namespace_path=package)

        self.assertEqual(second.graph_declaration, first.graph_declaration)


class GraphBlueprintValidationTests(unittest.TestCase):
    def test_a_graph_declaration_requires_a_purpose(self) -> None:
        blueprint = _empty_blueprint(_declaration())
        declaration = blueprint.graph_declaration
        assert declaration is not None
        object.__setattr__(declaration.meaning, "purpose", None)

        with self.assertRaisesRegex(ValueError, "purpose"):
            validate_blueprint(blueprint)

    def test_a_graph_declaration_meaning_must_be_a_meaning_value(self) -> None:
        blueprint = _empty_blueprint(_declaration())
        declaration = blueprint.graph_declaration
        assert declaration is not None
        object.__setattr__(declaration, "meaning", object())

        with self.assertRaisesRegex(ValueError, "Meaning with a purpose"):
            validate_blueprint(blueprint)

    def test_a_local_purpose_requires_a_graph_purpose(self) -> None:
        blueprint = GraphBlueprint(
            graph=GraphPartDTO(
                nodes=(
                    NodeDTO(
                        "site",
                        meaning=MeaningDTO(
                            purpose=PurposeDTO("The published register."),
                        ),
                    ),
                ),
            ),
            data=DataPartDTO(structs=(), source_relations=(), derived_relations=()),
            assets=AssetPartDTO(),
            bindings=(),
        )

        with self.assertRaisesRegex(ValueError, "local purpose"):
            validate_blueprint(blueprint)

    def test_claims_are_allowed_without_a_graph_purpose(self) -> None:
        blueprint = GraphBlueprint(
            graph=GraphPartDTO(
                nodes=(
                    NodeDTO(
                        "site",
                        meaning=MeaningDTO(
                            claims=(ClaimDTO("A site holds units."),),
                        ),
                    ),
                ),
            ),
            data=DataPartDTO(structs=(), source_relations=(), derived_relations=()),
            assets=AssetPartDTO(),
            bindings=(),
        )

        validate_blueprint(blueprint)


if __name__ == "__main__":
    unittest.main()
