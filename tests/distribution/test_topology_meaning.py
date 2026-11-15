"""Contract tests: meaning attachments on topology declarations.

The chain under test is authoring -> DTO -> document -> source. Every
declaration attaches the same ``Meaning`` value; a topology declaration may
carry one local purpose that narrows the graph purpose.
"""
from __future__ import annotations

import unittest

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
from kg_build_system.distribution.languages.topology import (
    AbstractNode,
    Edge,
    EdgeOptions,
    EdgeOptionsTemplate,
    EdgeTemplate,
    Node,
    NodeOptions,
    NodeOptionsTemplate,
    NodeTemplate,
    PropertySlot,
    property,
)
from kg_build_system.distribution.languages.topology.service.internal import (
    graph_from_document,
    graph_to_document,
    render_graph_source,
    transcribe_graph_part,
)


def _meaning() -> Meaning:
    return Meaning(
        purpose=Purpose(
            text="Scored associations.",
            limitations=(Limitation("Unscored evidence is absent."),),
        ),
        claims=(Claim("Scores are per datatype."),),
    )


def _meaning_dto() -> MeaningDTO:
    return MeaningDTO(
        purpose=PurposeDTO(
            "Scored associations.",
            (LimitationDTO("Unscored evidence is absent."),),
        ),
        claims=(ClaimDTO("Scores are per datatype."),),
    )


def _document() -> dict[str, object]:
    return {
        "purpose": {
            "text": "Scored associations.",
            "limitations": [{"text": "Unscored evidence is absent."}],
        },
        "claims": [{"text": "Scores are per datatype."}],
    }


class MeaningOptionTests(unittest.TestCase):
    def test_node_and_edge_options_carry_a_declaration_value(self) -> None:
        meaning = _meaning()

        self.assertIs(NodeOptions(meaning=meaning).meaning, meaning)
        self.assertIs(EdgeOptions(meaning=meaning).meaning, meaning)

    def test_template_options_carry_a_declaration_value(self) -> None:
        meaning = _meaning()

        self.assertIs(
            NodeOptionsTemplate(meaning=meaning).meaning, meaning,
        )
        self.assertIs(
            EdgeOptionsTemplate(meaning=meaning).meaning, meaning,
        )

    def test_an_attachment_rejects_a_non_meaning_value(self) -> None:
        for options in (
            NodeOptions,
            EdgeOptions,
            NodeOptionsTemplate,
            EdgeOptionsTemplate,
        ):
            with self.subTest(options=options.__name__):
                with self.assertRaisesRegex(TypeError, "must be a Meaning"):
                    options(meaning=object())  # type: ignore[arg-type]

    def test_property_rejects_a_non_meaning_value(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be a Meaning"):
            property(meaning=object())  # type: ignore[arg-type]


class MeaningTranscriptionTests(unittest.TestCase):
    def test_a_node_option_reaches_the_dto(self) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", meaning=_meaning())

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(part.nodes[0].meaning, _meaning_dto())

    def test_an_edge_option_reaches_the_dto(self) -> None:
        class SiteNode(Node):
            pass

        class UnitNode(Node):
            pass

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            options = EdgeOptions(name="has_unit", meaning=_meaning())

        part = transcribe_graph_part((HasUnitEdge,))

        self.assertEqual(part.edges[0].meaning, _meaning_dto())

    def test_a_property_meaning_reaches_the_property_dto(self) -> None:
        class SiteNode(Node):
            site_id: PropertySlot[str] = property(meaning=_meaning())

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(part.nodes[0].properties[0].meaning, _meaning_dto())

    def test_a_category_keeps_its_meaning_and_does_not_share_it(self) -> None:
        class DocumentedNode(AbstractNode):
            options = NodeOptions(name="documented", meaning=_meaning())

        class SiteNode(DocumentedNode, Node):
            pass

        part = transcribe_graph_part((DocumentedNode, SiteNode))
        nodes = {item.name: item for item in part.nodes}

        self.assertEqual(nodes["documented"].meaning, _meaning_dto())
        self.assertIsNone(nodes["site"].meaning)

    def test_a_node_template_contributes_its_meaning(self) -> None:
        class AuditedTemplate(NodeTemplate):
            options = NodeOptionsTemplate(meaning=_meaning())

        class SiteNode(AuditedTemplate, Node):
            pass

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(part.nodes[0].meaning, _meaning_dto())

    def test_an_edge_template_contributes_its_meaning(self) -> None:
        class AuditedTemplate(EdgeTemplate):
            options = EdgeOptionsTemplate(meaning=_meaning())

        class SiteNode(Node):
            pass

        class UnitNode(Node):
            pass

        class HasUnitEdge(AuditedTemplate, Edge[SiteNode, UnitNode]):
            pass

        part = transcribe_graph_part((HasUnitEdge,))

        self.assertEqual(part.edges[0].meaning, _meaning_dto())

    def test_own_options_override_a_template_meaning(self) -> None:
        class AuditedTemplate(NodeTemplate):
            options = NodeOptionsTemplate(meaning=_meaning())

        own = Meaning(claims=(Claim("The host owns its meaning."),))

        class SiteNode(AuditedTemplate, Node):
            options = NodeOptions(name="site", meaning=own)

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(
            part.nodes[0].meaning,
            MeaningDTO(claims=(ClaimDTO("The host owns its meaning."),)),
        )


class MeaningDocumentTests(unittest.TestCase):
    def test_node_edge_and_property_documents_carry_meaning(self) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", meaning=_meaning())
            site_id: PropertySlot[str] = property(meaning=_meaning())

        class UnitNode(Node):
            pass

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            options = EdgeOptions(name="has_unit", meaning=_meaning())

        part = transcribe_graph_part((SiteNode, HasUnitEdge))
        document = graph_to_document(part)

        self.assertEqual(document["nodes"][0]["meaning"], _document())
        self.assertEqual(document["nodes"][0]["properties"][0]["meaning"], _document())
        self.assertEqual(document["edges"][0]["meaning"], _document())
        self.assertEqual(graph_from_document(document), part)

    def test_a_declaration_without_meaning_writes_no_member(self) -> None:
        class SiteNode(Node):
            site_id: PropertySlot[str] = property()

        part = transcribe_graph_part((SiteNode,))
        document = graph_to_document(part)

        self.assertNotIn("meaning", document["nodes"][0])
        self.assertNotIn("meaning", document["nodes"][0]["properties"][0])


class MeaningSourceTests(unittest.TestCase):
    def test_node_edge_and_property_source_embed_the_shared_renderer(
        self,
    ) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", meaning=_meaning())
            site_id: PropertySlot[str] = property(meaning=_meaning())

        class UnitNode(Node):
            pass

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            options = EdgeOptions(name="has_unit", meaning=_meaning())

        fragment = render_graph_source(
            transcribe_graph_part((SiteNode, HasUnitEdge)), None,
        )

        self.assertIn("        meaning=Meaning(", fragment.body)
        self.assertIn("            purpose=Purpose(", fragment.body)
        self.assertIn("                    Limitation(", fragment.body)
        self.assertIn(
            "from kg_build_system import Claim, Limitation, Purpose, Meaning",
            fragment.imports,
        )
        compile(
            "\n".join(fragment.imports) + "\n" + fragment.body,
            "<topology-meaning>",
            "exec",
        )

    def test_authoring_to_document_to_source_preserves_the_units(self) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", meaning=_meaning())

        part = transcribe_graph_part((SiteNode,))
        document = graph_to_document(part)
        fragment = render_graph_source(graph_from_document(document), None)

        self.assertEqual(document["nodes"][0]["meaning"], _document())
        self.assertIn("Claim('Scores are per datatype.'),", fragment.body)
        self.assertIn("purpose=Purpose(", fragment.body)
        self.assertIn("Limitation('Unscored evidence is absent.'),", fragment.body)


if __name__ == "__main__":
    unittest.main()
