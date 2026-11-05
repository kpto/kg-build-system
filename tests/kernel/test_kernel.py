from __future__ import annotations

import unittest

from kg_build_system.kernel import (
    Declaration,
    Key,
    Language,
    SourceFragment,
    Symbol,
    SymbolContext,
    SymbolRef,
    Toolchain,
    WorkflowRuntime,
)


class _Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


class EchoLanguage:
    name = "echo"

    def discover_declarations(self, namespace):
        return tuple(Declaration(value) for value in namespace.values())

    def compute_key(self, declaration):
        return Key((str(declaration.value),))

    def get_kind(self, declaration):
        return "echo"

    def get_identity(self, value):
        if not isinstance(value, str):
            return None
        return SymbolRef(self.name, Key((value,)))

    def get_references(self, value, resolver):
        del value, resolver
        return ()

    def transcribe(self, declaration, context):
        del context
        key = self.compute_key(declaration)
        return Symbol(key, "echo", declaration.value)

    def render(self, symbol, context):
        del context
        return SourceFragment("inline", repr(symbol.value))


class ConsumerLanguage(EchoLanguage):
    name = "consumer"

    def discover_declarations(self, namespace):
        del namespace
        return (Declaration("consumer"),)

    def compute_key(self, declaration):
        del declaration
        return Key(("consumer",))

    def get_identity(self, value):
        if value != "consumer":
            return None
        return SymbolRef(self.name, Key(("consumer",)))

    def transcribe(self, declaration, context):
        del declaration
        value = tuple(context.symbols.values())
        key = Key(("consumer",))
        return Symbol(key, "echo", value)


class RecordingLinker:
    def __init__(self) -> None:
        self.languages = None
        self.namespace = None

    def link(self, languages, namespace):
        self.languages = tuple(languages)
        self.namespace = namespace
        model: dict[SymbolRef, Symbol] = {}
        for language in languages:
            declarations = tuple(
                language.discover_declarations(namespace)
            )
            for declaration in declarations:
                symbol = language.transcribe(
                    declaration, SymbolContext(model),
                )
                model[SymbolRef(language.name, symbol.key)] = symbol
        return model


class Resources:
    def resources(self, configuration):
        return {}

    def close(self):
        return None


def _toolchain(*languages: object) -> Toolchain[object]:
    return Toolchain(
        languages=languages,
        linker=RecordingLinker(),
        runtime=WorkflowRuntime(providers=(Resources(),)),
    )


class KeyTests(unittest.TestCase):
    def test_a_key_extends_with_child_segments(self) -> None:
        key = Key(("site",)).child("name")
        self.assertEqual(key, Key(("site", "name")))
        self.assertEqual(Key(()).child("a", "b"), Key(("a", "b")))

    def test_starts_with_tests_a_prefix(self) -> None:
        self.assertTrue(Key(("site", "name")).starts_with(Key(("site",))))
        self.assertTrue(Key(("site",)).starts_with(Key(())))
        self.assertFalse(Key(("site",)).starts_with(Key(("site", "name"))))

    def test_matches_supports_segment_wildcards_and_a_final_double_star(self) -> None:
        self.assertTrue(Key(("site", "name")).matches(Key(("site", "*"))))
        self.assertTrue(Key(("site", "name", "value")).matches(
            Key(("site", "**")),
        ))
        self.assertTrue(Key(("site",)).matches(Key(("site",))))
        self.assertFalse(Key(("other", "name")).matches(Key(("site", "*"))))
        self.assertFalse(Key(("site", "name", "value")).matches(
            Key(("site",)),
        ))

    def test_a_key_round_trips_to_a_document_and_text(self) -> None:
        key = Key(("site", "name"))
        self.assertEqual(key.to_document(), ["site", "name"])
        self.assertEqual(str(key), "site/name")
        self.assertEqual(hash(key), hash(Key(("site", "name"))))


class SymbolModelTests(unittest.TestCase):
    def test_a_symbol_context_reads_symbols_and_values(self) -> None:
        reference = SymbolRef("echo", Key(("hello",)))
        symbol = Symbol(reference.key, "echo", "hello")
        context = SymbolContext({reference: symbol})

        self.assertIs(context.get_symbol(reference), symbol)
        self.assertEqual(context.get_value(reference), "hello")

    def test_a_symbol_context_refuses_an_unknown_reference(self) -> None:
        context = SymbolContext()
        with self.assertRaisesRegex(KeyError, "unknown symbol"):
            context.get_symbol(SymbolRef("echo", Key(("missing",))))

    def test_a_symbol_context_copies_its_mapping(self) -> None:
        reference = SymbolRef("echo", Key(("hello",)))
        symbols = {reference: Symbol(reference.key, "echo", "hello")}
        context = SymbolContext(symbols)

        symbols.clear()

        self.assertEqual(context.get_value(reference), "hello")


class KernelTests(unittest.TestCase):
    def test_the_toolchain_hands_languages_and_namespace_to_the_linker(self) -> None:
        linker = RecordingLinker()
        toolchain = Toolchain(
            languages=(EchoLanguage(), ConsumerLanguage()),
            linker=linker,
        )
        namespace = _Namespace(1, 2)

        model = toolchain.build(namespace)

        self.assertIs(linker.namespace, namespace)
        self.assertEqual(
            [language.name for language in linker.languages],
            ["echo", "consumer"],
        )
        self.assertIsInstance(model, dict)

    def test_a_language_produces_one_symbol_per_declaration(self) -> None:
        model = _toolchain(EchoLanguage()).build(_Namespace("a", "b"))

        self.assertEqual(
            set(model),
            {
                SymbolRef("echo", Key(("a",))),
                SymbolRef("echo", Key(("b",))),
            },
        )
        self.assertEqual(
            [symbol.value for symbol in model.values()],
            ["a", "b"],
        )

    def test_a_later_language_reads_the_earlier_symbol_context(self) -> None:
        model = _toolchain(EchoLanguage(), ConsumerLanguage()).build(
            _Namespace("a", "b"),
        )
        consumer = model[SymbolRef("consumer", Key(("consumer",)))]
        self.assertEqual(
            [symbol.value for symbol in consumer.value],
            ["a", "b"],
        )

    def test_a_language_reports_the_identity_of_its_values(self) -> None:
        language = EchoLanguage()
        self.assertEqual(
            language.get_identity("hello"),
            SymbolRef("echo", Key(("hello",))),
        )
        self.assertIsNone(language.get_identity(1))

    def test_the_language_protocol_is_structural(self) -> None:
        language: Language = EchoLanguage()
        self.assertEqual(language.name, "echo")


if __name__ == "__main__":
    unittest.main()
