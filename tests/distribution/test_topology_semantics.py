"""Contract tests: semantics attachments on topology declarations.

The chain under test is authoring -> DTO -> document -> source. A topology
declaration attaches a declaration fragment, ``Semantics``, never the graph
meaning root, ``GraphSemantics``.
"""
from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.semantics.model.internal import (
    ClaimDTO,
    FrameDTO,
    LimitationDTO,
    SemanticsDTO,
)
from kg_build_system.distribution.languages.semantics.model.public import (
    Claim,
    Frame,
    GraphSemantics,
    Limitation,
    Purpose,
    Semantics,
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


def _semantics() -> Semantics:
    return Semantics(
        claims=(Claim("Scores are per datatype."),),
        frames=(
            Frame(
                text="Scored associations.",
                limitations=(Limitation("Unscored evidence is absent."),),
            ),
        ),
    )


def _semantics_dto() -> SemanticsDTO:
    return SemanticsDTO(
        claims=(ClaimDTO("Scores are per datatype."),),
        frames=(
            FrameDTO(
                "Scored associations.",
                (LimitationDTO("Unscored evidence is absent."),),
            ),
        ),
    )


def _graph_semantics() -> GraphSemantics:
    return GraphSemantics(purpose=Purpose("Target prioritisation."))


def _document() -> dict[str, object]:
    return {
        "claims": [{"text": "Scores are per datatype."}],
        "frames": [
            {
                "text": "Scored associations.",
                "limitations": [{"text": "Unscored evidence is absent."}],
            },
        ],
    }


class SemanticsOptionTests(unittest.TestCase):
    def test_node_and_edge_options_carry_a_declaration_fragment(self) -> None:
        semantics = _semantics()

        self.assertIs(NodeOptions(semantics=semantics).semantics, semantics)
        self.assertIs(EdgeOptions(semantics=semantics).semantics, semantics)

    def test_template_options_carry_a_declaration_fragment(self) -> None:
        semantics = _semantics()

        self.assertIs(
            NodeOptionsTemplate(semantics=semantics).semantics, semantics,
        )
        self.assertIs(
            EdgeOptionsTemplate(semantics=semantics).semantics, semantics,
        )

    def test_an_attachment_rejects_the_graph_meaning_root(self) -> None:
        graph_semantics = _graph_semantics()

        for options in (
            NodeOptions,
            EdgeOptions,
            NodeOptionsTemplate,
            EdgeOptionsTemplate,
        ):
            with self.subTest(options=options.__name__):
                with self.assertRaisesRegex(TypeError, "not GraphSemantics"):
                    options(semantics=graph_semantics)

    def test_property_rejects_the_graph_meaning_root(self) -> None:
        with self.assertRaisesRegex(TypeError, "not GraphSemantics"):
            property(semantics=_graph_semantics())


class SemanticsTranscriptionTests(unittest.TestCase):
    def test_a_node_option_reaches_the_dto(self) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", semantics=_semantics())

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(part.nodes[0].semantics, _semantics_dto())

    def test_an_edge_option_reaches_the_dto(self) -> None:
        class SiteNode(Node):
            pass

        class UnitNode(Node):
            pass

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            options = EdgeOptions(name="has_unit", semantics=_semantics())

        part = transcribe_graph_part((HasUnitEdge,))

        self.assertEqual(part.edges[0].semantics, _semantics_dto())

    def test_a_property_semantics_reaches_the_property_dto(self) -> None:
        class SiteNode(Node):
            site_id: PropertySlot[str] = property(semantics=_semantics())

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(part.nodes[0].properties[0].semantics, _semantics_dto())

    def test_a_category_keeps_its_semantics_and_does_not_share_it(self) -> None:
        class DocumentedNode(AbstractNode):
            options = NodeOptions(name="documented", semantics=_semantics())

        class SiteNode(DocumentedNode, Node):
            pass

        part = transcribe_graph_part((DocumentedNode, SiteNode))
        nodes = {item.name: item for item in part.nodes}

        self.assertEqual(nodes["documented"].semantics, _semantics_dto())
        self.assertIsNone(nodes["site"].semantics)

    def test_a_node_template_contributes_its_semantics(self) -> None:
        class AuditedTemplate(NodeTemplate):
            options = NodeOptionsTemplate(semantics=_semantics())

        class SiteNode(AuditedTemplate, Node):
            pass

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(part.nodes[0].semantics, _semantics_dto())

    def test_an_edge_template_contributes_its_semantics(self) -> None:
        class AuditedTemplate(EdgeTemplate):
            options = EdgeOptionsTemplate(semantics=_semantics())

        class SiteNode(Node):
            pass

        class UnitNode(Node):
            pass

        class HasUnitEdge(AuditedTemplate, Edge[SiteNode, UnitNode]):
            pass

        part = transcribe_graph_part((HasUnitEdge,))

        self.assertEqual(part.edges[0].semantics, _semantics_dto())

    def test_own_options_override_a_template_semantics(self) -> None:
        class AuditedTemplate(NodeTemplate):
            options = NodeOptionsTemplate(semantics=_semantics())

        own = Semantics(claims=(Claim("The host owns its meaning."),))

        class SiteNode(AuditedTemplate, Node):
            options = NodeOptions(name="site", semantics=own)

        part = transcribe_graph_part((SiteNode,))

        self.assertEqual(
            part.nodes[0].semantics,
            SemanticsDTO(claims=(ClaimDTO("The host owns its meaning."),)),
        )


class SemanticsDocumentTests(unittest.TestCase):
    def test_node_edge_and_property_documents_carry_semantics(self) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", semantics=_semantics())
            site_id: PropertySlot[str] = property(semantics=_semantics())

        class UnitNode(Node):
            pass

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            options = EdgeOptions(name="has_unit", semantics=_semantics())

        part = transcribe_graph_part((SiteNode, HasUnitEdge))
        document = graph_to_document(part)

        self.assertEqual(document["nodes"][0]["semantics"], _document())
        self.assertEqual(document["nodes"][0]["properties"][0]["semantics"], _document())
        self.assertEqual(document["edges"][0]["semantics"], _document())
        self.assertEqual(graph_from_document(document), part)

    def test_a_declaration_without_semantics_writes_no_member(self) -> None:
        class SiteNode(Node):
            site_id: PropertySlot[str] = property()

        part = transcribe_graph_part((SiteNode,))
        document = graph_to_document(part)

        self.assertNotIn("semantics", document["nodes"][0])
        self.assertNotIn("semantics", document["nodes"][0]["properties"][0])

class SemanticsSourceTests(unittest.TestCase):
    def test_node_edge_and_property_source_embed_the_shared_renderer(
        self,
    ) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", semantics=_semantics())
            site_id: PropertySlot[str] = property(semantics=_semantics())

        class UnitNode(Node):
            pass

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            options = EdgeOptions(name="has_unit", semantics=_semantics())

        fragment = render_graph_source(
            transcribe_graph_part((SiteNode, HasUnitEdge)), None,
        )

        self.assertIn("        semantics=Semantics(", fragment.body)
        self.assertIn("            claims=(", fragment.body)
        self.assertIn("                    Limitation(", fragment.body)
        self.assertIn(
            "from kg_build_system import Claim, Frame, Limitation, Semantics",
            fragment.imports,
        )
        compile(
            "\n".join(fragment.imports) + "\n" + fragment.body,
            "<topology-semantics>",
            "exec",
        )

    def test_authoring_to_document_to_source_preserves_the_units(self) -> None:
        class SiteNode(Node):
            options = NodeOptions(name="site", semantics=_semantics())

        part = transcribe_graph_part((SiteNode,))
        document = graph_to_document(part)
        fragment = render_graph_source(graph_from_document(document), None)

        self.assertEqual(document["nodes"][0]["semantics"], _document())
        self.assertIn("Claim('Scores are per datatype.'),", fragment.body)
        self.assertIn("Frame(", fragment.body)
        self.assertIn("Limitation('Unscored evidence is absent.'),", fragment.body)


if __name__ == "__main__":
    unittest.main()
