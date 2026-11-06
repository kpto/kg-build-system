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
from kg_build_system.distribution.languages.semantics.model.internal.dto import (
    ClaimDTO,
    FrameDTO,
    GraphSemanticsDTO,
    LimitationDTO,
    PurposeDTO,
)
from kg_build_system.distribution.languages.semantics.model.public import (
    Claim,
    Frame,
    GraphSemantics,
    Limitation,
    Purpose,
)
from kg_build_system.kernel import (
    Declaration,
    Key,
    Symbol,
    SymbolContext,
    SymbolRef,
)


def _semantics() -> GraphSemantics:
    return GraphSemantics(
        claims=(Claim("associations are scored per datatype"),),
        purpose=Purpose(
            text="rank targets for a disease",
            frames=(
                Frame(
                    text="curated evidence only",
                    limitations=(Limitation("no literature mining"),),
                ),
            ),
        ),
    )


def _semantics_dto() -> GraphSemanticsDTO:
    return GraphSemanticsDTO(
        claims=(ClaimDTO("associations are scored per datatype"),),
        purpose=PurposeDTO(
            text="rank targets for a disease",
            frames=(
                FrameDTO(
                    text="curated evidence only",
                    limitations=(LimitationDTO("no literature mining"),),
                ),
            ),
        ),
    )


def _options(
    name: str | None = None,
    description: str | None = "Curated target-disease evidence.",
) -> GraphOptions:
    return GraphOptions(
        name=name,
        description=description,
        semantics=_semantics(),
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
        semantics=_semantics_dto(),
    )


class GraphOptionsTests(unittest.TestCase):
    def test_semantics_is_required(self) -> None:
        with self.assertRaises(TypeError):
            GraphOptions()  # type: ignore[call-arg]

    def test_semantics_must_be_graph_semantics(self) -> None:
        with self.assertRaises(TypeError):
            GraphOptions(semantics=object())  # type: ignore[arg-type]

    def test_semantics_must_carry_a_purpose(self) -> None:
        semantics = _semantics()
        object.__setattr__(semantics, "purpose", object())

        with self.assertRaises(TypeError):
            GraphOptions(semantics=semantics)

    def test_name_and_description_are_optional_non_empty_text(self) -> None:
        options = GraphOptions(semantics=_semantics())
        self.assertIsNone(options.name)
        self.assertIsNone(options.description)

        with self.assertRaises(ValueError):
            GraphOptions(name="", semantics=_semantics())
        with self.assertRaises(ValueError):
            GraphOptions(description="", semantics=_semantics())

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
                semantics=_semantics_dto(),
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
            document["semantics"]["claims"],
            [{"text": "associations are scored per datatype"}],
        )
        self.assertEqual(
            document["semantics"]["purpose"]["frames"][0]["limitations"],
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
            semantics=GraphSemanticsDTO(
                purpose=PurposeDTO(text="rank targets for a disease"),
            ),
        )

        document = graph_declaration_to_document(value)

        self.assertNotIn("claims", document["semantics"])
        self.assertEqual(graph_declaration_from_document(document), value)

    def test_a_graph_declaration_requires_name_and_semantics(self) -> None:
        with self.assertRaises(ValueError):
            graph_declaration_from_document({})
        with self.assertRaises(ValueError):
            graph_declaration_from_document(
                {"name": "", "semantics": {"purpose": {"text": "p"}}}
            )
        with self.assertRaises(ValueError):
            graph_declaration_from_document({"name": "open_targets"})
        with self.assertRaises(ValueError):
            graph_declaration_from_document(
                {"name": "open_targets", "semantics": 1}
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
        self.assertIn("semantics=GraphSemantics(", fragment.body)
        self.assertIn("purpose=Purpose(", fragment.body)
        self.assertIn("from kg_build_system import Graph", fragment.imports)
        self.assertIn(
            "from kg_build_system import GraphOptions", fragment.imports,
        )
        self.assertTrue(
            any("GraphSemantics" in item for item in fragment.imports)
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
