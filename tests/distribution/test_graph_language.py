from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.graph import Graph, GraphOptions
from kg_build_system.distribution.languages.graph.model.internal.dto import (
    GraphDeclarationDTO,
)
from kg_build_system.distribution.languages.graph.service.internal import (
    GraphLanguage,
    graph_declaration_from_document,
    graph_declaration_to_document,
    render_graph_declaration_source,
)
from kg_build_system.distribution.languages.meaning.model.internal.dto import (
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
from kg_build_system.kernel import (
    Declaration,
    Key,
    Symbol,
    SymbolContext,
    SymbolRef,
)


def _meaning() -> Meaning:
    return Meaning(
        purpose=Purpose(
            text="rank targets for a disease",
            limitations=(Limitation("no literature mining"),),
        ),
        claims=(Claim("associations are scored per datatype"),),
    )


def _meaning_dto() -> MeaningDTO:
    return MeaningDTO(
        purpose=PurposeDTO(
            text="rank targets for a disease",
            limitations=(LimitationDTO("no literature mining"),),
        ),
        claims=(ClaimDTO("associations are scored per datatype"),),
    )


def _options(
    name: str | None = None,
    description: str | None = "Curated target-disease evidence.",
) -> GraphOptions:
    return GraphOptions(
        name=name,
        description=description,
        meaning=_meaning(),
    )


def _declaration(name: str | None = None) -> type[Graph]:
    class OpenTargets(Graph):
        options = _options(name)

    return OpenTargets


def _dto(
    name: str = "open_targets",
    description: str | None = "Curated target-disease evidence.",
) -> GraphDeclarationDTO:
    return GraphDeclarationDTO(
        name=name,
        description=description,
        meaning=_meaning_dto(),
    )


class GraphOptionsTests(unittest.TestCase):
    def test_meaning_is_required(self) -> None:
        with self.assertRaises(TypeError):
            GraphOptions()  # type: ignore[call-arg]

    def test_meaning_must_be_a_meaning_value(self) -> None:
        with self.assertRaises(TypeError):
            GraphOptions(meaning=object())  # type: ignore[arg-type]

    def test_meaning_must_carry_a_purpose(self) -> None:
        with self.assertRaisesRegex(TypeError, "requires a Meaning with a purpose"):
            GraphOptions(
                meaning=Meaning(claims=(Claim("A claim."),)),
            )

    def test_name_and_description_are_optional_non_empty_text(self) -> None:
        options = GraphOptions(meaning=_meaning())
        self.assertIsNone(options.name)
        self.assertIsNone(options.description)

        with self.assertRaises(ValueError):
            GraphOptions(name="", meaning=_meaning())
        with self.assertRaises(ValueError):
            GraphOptions(description="", meaning=_meaning())

    def test_options_are_frozen(self) -> None:
        options = _options()

        with self.assertRaises(AttributeError):
            options.name = "other"  # type: ignore[misc]


class GraphDeclarationTests(unittest.TestCase):
    def test_the_name_defaults_to_the_snake_case_class_name(self) -> None:
        declaration = _declaration()

        self.assertEqual(declaration._graph_name, "open_targets")
        self.assertIs(declaration._graph_options, declaration.options)

    def test_an_explicit_name_wins(self) -> None:
        declaration = _declaration("target_graph")
        self.assertEqual(declaration._graph_name, "target_graph")

    def test_a_declaration_requires_graph_options(self) -> None:
        with self.assertRaises(TypeError):
            class Missing(Graph):
                pass

        with self.assertRaises(TypeError):
            class Wrong(Graph):
                options = object()


class GraphDiscoveryTests(unittest.TestCase):
    def test_zero_declarations_are_allowed(self) -> None:
        class Namespace:
            def values(self):
                return (Graph, 1, "not a graph")

        declarations = tuple(
            GraphLanguage().discover_declarations(Namespace())
        )

        self.assertEqual(declarations, ())

    def test_one_declaration_is_discovered(self) -> None:
        declaration = _declaration()

        class Namespace:
            def values(self):
                return (Graph, declaration, 1)

        declarations = tuple(
            GraphLanguage().discover_declarations(Namespace())
        )

        self.assertEqual(len(declarations), 1)
        self.assertIs(declarations[0].value, declaration)

    def test_two_declarations_raise(self) -> None:
        first = _declaration("first")
        second = _declaration("second")

        class Namespace:
            def values(self):
                return (first, second)

        with self.assertRaisesRegex(ValueError, "at most one Graph"):
            tuple(GraphLanguage().discover_declarations(Namespace()))

    def test_the_same_declaration_is_not_counted_twice(self) -> None:
        declaration = _declaration()

        class Namespace:
            def values(self):
                return (declaration, declaration)

        declarations = tuple(
            GraphLanguage().discover_declarations(Namespace())
        )

        self.assertEqual(len(declarations), 1)


class GraphLanguageTests(unittest.TestCase):
    def test_key_kind_identity_and_references(self) -> None:
        declaration = _declaration()
        language = GraphLanguage()
        item = Declaration(declaration)

        self.assertEqual(language.compute_key(item), Key(("open_targets",)))
        self.assertEqual(language.get_kind(item), "graph")
        self.assertEqual(
            language.get_identity(declaration),
            SymbolRef("graph", Key(("open_targets",))),
        )
        self.assertEqual(language.get_references(declaration, None), ())
        self.assertIsNone(language.get_identity(1))

    def test_transcription_produces_a_graph_declaration_dto(self) -> None:
        declaration = _declaration()
        language = GraphLanguage()

        symbol = language.transcribe(
            Declaration(declaration), SymbolContext(),
        )

        self.assertIsInstance(symbol.value, GraphDeclarationDTO)
        self.assertEqual(symbol.key, Key(("open_targets",)))
        self.assertEqual(symbol.kind, "graph")
        self.assertEqual(symbol.references, ())
        self.assertEqual(
            symbol.value,
            GraphDeclarationDTO(
                name="open_targets",
                description="Curated target-disease evidence.",
                meaning=_meaning_dto(),
            ),
        )

    def test_transcription_rejects_a_non_graph_value(self) -> None:
        with self.assertRaises(TypeError):
            GraphLanguage().transcribe(Declaration(1), SymbolContext())


class GraphCodecTests(unittest.TestCase):
    def test_the_graph_declaration_round_trips(self) -> None:
        value = _dto()

        document = graph_declaration_to_document(value)

        self.assertEqual(document["name"], "open_targets")
        self.assertEqual(
            document["description"], "Curated target-disease evidence.",
        )
        self.assertEqual(
            document["meaning"]["claims"],
            [{"text": "associations are scored per datatype"}],
        )
        self.assertEqual(
            document["meaning"]["purpose"]["limitations"],
            [{"text": "no literature mining"}],
        )
        self.assertEqual(graph_declaration_from_document(document), value)

    def test_an_absent_description_is_omitted_and_decodes_to_none(self) -> None:
        value = _dto(description=None)

        document = graph_declaration_to_document(value)

        self.assertNotIn("description", document)
        self.assertIsNone(
            graph_declaration_from_document(document).description
        )

    def test_an_empty_claim_list_is_omitted(self) -> None:
        value = GraphDeclarationDTO(
            name="open_targets",
            description=None,
            meaning=MeaningDTO(
                purpose=PurposeDTO(text="rank targets for a disease"),
            ),
        )

        document = graph_declaration_to_document(value)

        self.assertNotIn("claims", document["meaning"])
        self.assertEqual(graph_declaration_from_document(document), value)

    def test_a_graph_declaration_requires_name_and_meaning(self) -> None:
        with self.assertRaises(ValueError):
            graph_declaration_from_document({})
        with self.assertRaises(ValueError):
            graph_declaration_from_document(
                {"name": "", "meaning": {"purpose": {"text": "p"}}}
            )
        with self.assertRaises(ValueError):
            graph_declaration_from_document({"name": "open_targets"})
        with self.assertRaises(ValueError):
            graph_declaration_from_document(
                {"name": "open_targets", "meaning": 1}
            )

    def test_a_graph_declaration_document_requires_a_purpose(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires a purpose"):
            graph_declaration_from_document(
                {
                    "name": "open_targets",
                    "meaning": {"claims": [{"text": "A claim."}]},
                }
            )

    def test_a_graph_dto_rejects_meaning_without_a_purpose(self) -> None:
        with self.assertRaisesRegex(ValueError, "Meaning with a purpose"):
            GraphDeclarationDTO(
                name="open_targets",
                description=None,
                meaning=MeaningDTO(claims=(ClaimDTO("A claim."),)),
            )


class GraphSourceTests(unittest.TestCase):
    def test_the_source_render_is_a_graph_option_declaration(self) -> None:
        fragment = render_graph_declaration_source(_dto())

        self.assertEqual(fragment.kind, "declaration")
        self.assertIn("class OpenTargetsGraph(Graph):", fragment.body)
        self.assertIn("options = GraphOptions(", fragment.body)
        self.assertIn("name='open_targets'", fragment.body)
        self.assertIn(
            "description='Curated target-disease evidence.'", fragment.body,
        )
        self.assertIn("meaning=Meaning(", fragment.body)
        self.assertIn("purpose=Purpose(", fragment.body)
        self.assertIn("from kg_build_system import Graph", fragment.imports)
        self.assertIn(
            "from kg_build_system import GraphOptions", fragment.imports,
        )
        self.assertTrue(
            any("Meaning" in item for item in fragment.imports)
        )
        self.assertTrue(any("Purpose" in item for item in fragment.imports))

    def test_an_absent_description_is_not_rendered(self) -> None:
        fragment = render_graph_declaration_source(_dto(description=None))

        self.assertNotIn("description=", fragment.body)

    def test_the_language_renders_a_symbol_or_a_dto(self) -> None:
        value = _dto()
        language = GraphLanguage()
        symbol = Symbol(
            Key(("open_targets",)), "graph", value,
        )

        self.assertEqual(
            language.render(symbol, None).body,
            render_graph_declaration_source(value).body,
        )
        self.assertEqual(
            language.render(value, None).body,
            render_graph_declaration_source(value).body,
        )

    def test_the_rendered_source_is_python(self) -> None:
        fragment = render_graph_declaration_source(_dto())

        compile(fragment.body, "<graph>", "exec")


if __name__ == "__main__":
    unittest.main()
