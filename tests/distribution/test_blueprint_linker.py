from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from kg_build_system.distribution.interpreter import GraphBlueprint
from kg_build_system.distribution.interpreter.service.internal import (
    BlueprintLinker,
)
from kg_build_system.distribution.languages.asset.service.internal import (
    AssetLanguage,
)
from kg_build_system.distribution.languages.binding.service.internal import (
    BindingLanguage,
)
from kg_build_system.distribution.languages.data.model.internal import (
    DataPartDTO,
    StructDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    DataLanguage,
)
from kg_build_system.distribution.languages.data import (
    Field,
    Struct,
    StructOptions,
    Table,
    TableOptions,
    field,
)
from kg_build_system.distribution.languages.topology.model.internal import (
    GraphPartDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    ExpressionsLanguage,
)
from kg_build_system.distribution.languages.topology.service.internal import (
    TopologyLanguage,
)
from kg_build_system.kernel import (
    Declaration,
    Key,
    SourceFragment,
    Symbol,
    SymbolContext,
    SymbolRef,
)
from .support import TestEstate


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


def _languages():
    return (
        ExpressionsLanguage(), AssetLanguage(), DataLanguage(),
        TopologyLanguage(), BindingLanguage(),
    )


@dataclass(frozen=True)
class ProbeValue:
    """One authoring value a probe language offers to the linker."""

    owner: str
    name: str
    references: tuple[SymbolRef, ...] = ()
    payload: Any = None


class ProbeLanguage:
    """A minimal language with per-declaration transcription."""

    def __init__(
        self, name: str, values: tuple[ProbeValue, ...] = (),
    ) -> None:
        self.name = name
        self.values = values
        self.transcribed: list[str] = []

    def discover_declarations(self, namespace):
        del namespace
        return tuple(Declaration(value) for value in self.values)

    def compute_key(self, declaration):
        return Key((declaration.value.name,))

    def get_kind(self, declaration):
        del declaration
        return "probe"

    def get_identity(self, value):
        if not isinstance(value, ProbeValue) or value.owner != self.name:
            return None
        return SymbolRef(self.name, Key((value.name,)))

    def get_references(self, value, resolver):
        del resolver
        if not isinstance(value, ProbeValue):
            return ()
        return value.references

    def transcribe(self, declaration, context):
        del context
        value = declaration.value
        self.transcribed.append(value.name)
        return Symbol(
            Key((value.name,)),
            "probe",
            value if value.payload is None else value.payload,
        )

    def render(self, symbol, context):
        del context
        return SourceFragment("inline", repr(symbol.value))


class BatchProbeLanguage(ProbeLanguage):
    """A batch implementation hidden behind the per-declaration method."""

    def discover_declarations(self, namespace):
        declarations = super().discover_declarations(namespace)
        self._batch = {
            value.name: Symbol(Key((value.name,)), "probe", value)
            for value in self.values
        }
        return declarations

    def transcribe(self, declaration, context):
        del context
        value = declaration.value
        self.transcribed.append(value.name)
        return self._batch[value.name]


def _probe_languages(**values: tuple[ProbeValue, ...]):
    return (
        ProbeLanguage("expressions", values.get("expressions", ())),
        ProbeLanguage("asset", values.get("asset", ())),
        ProbeLanguage("data", values.get("data", ())),
        ProbeLanguage("topology", values.get("topology", ())),
        ProbeLanguage("binding", values.get("binding", ())),
    )


def _data_declarations(language, namespace):
    return tuple(
        declaration
        for declaration in language.discover_declarations(namespace)
        if isinstance(declaration.value, type)
    )


class BlueprintLinkerTests(unittest.TestCase):
    def test_the_linker_requires_every_default_language(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "requires languages expressions, asset, binding",
        ):
            BlueprintLinker().link(
                (DataLanguage(), TopologyLanguage()), Namespace(),
            )

    def test_linking_an_empty_namespace_returns_an_empty_blueprint(self) -> None:
        linked = BlueprintLinker().link(_languages(), Namespace())

        self.assertIsInstance(linked, GraphBlueprint)
        self.assertEqual(linked.graph, GraphPartDTO())
        self.assertEqual(
            linked.data,
            DataPartDTO(structs=(), relations=(), projections=()),
        )
        self.assertEqual(linked.assets.assets, ())
        self.assertEqual(linked.bindings, ())

    def test_languages_are_indexed_in_dependency_order(self) -> None:
        calls: list[str] = []

        class RecordingExpressions(ExpressionsLanguage):
            def discover_declarations(self, namespace):
                calls.append("expressions")
                return super().discover_declarations(namespace)

        class RecordingAsset(AssetLanguage):
            def discover_declarations(self, namespace):
                calls.append("asset")
                return super().discover_declarations(namespace)

        class RecordingData(DataLanguage):
            def discover_declarations(self, namespace):
                calls.append("data")
                return super().discover_declarations(namespace)

        class RecordingTopology(TopologyLanguage):
            def discover_declarations(self, namespace):
                calls.append("topology")
                return super().discover_declarations(namespace)

        class RecordingBinding(BindingLanguage):
            def discover_declarations(self, namespace):
                calls.append("binding")
                return super().discover_declarations(namespace)

        BlueprintLinker().link(
            (
                RecordingBinding(), RecordingTopology(), RecordingData(),
                RecordingAsset(), RecordingExpressions(),
            ),
            Namespace(),
        )

        self.assertEqual(
            calls, ["expressions", "asset", "data", "topology", "binding"],
        )

    def test_a_declaration_key_is_indexed_once(self) -> None:
        language = ProbeLanguage("data", (
            ProbeValue("data", "same"), ProbeValue("data", "same"),
        ))

        with self.assertRaisesRegex(ValueError, "declares key same twice"):
            BlueprintLinker(roots=("data",)).link(
                _probe_languages(data=language.values), Namespace(),
            )

    def test_a_fake_language_produces_symbols_for_the_blueprint(self) -> None:
        language = ProbeLanguage("data", (
            ProbeValue(
                "data", "broken", payload=StructDTO("broken", ()),
            ),
        ))

        linked = BlueprintLinker(roots=("data",)).link(
            (
                ProbeLanguage("expressions"), ProbeLanguage("asset"),
                language, ProbeLanguage("topology"),
                ProbeLanguage("binding"),
            ),
            Namespace(),
        )

        self.assertEqual(
            linked.data.structs, (StructDTO("broken", ()),),
        )
        self.assertEqual(language.transcribed, ["broken"])

    def test_a_missing_symbol_reference_is_refused(self) -> None:
        missing = SymbolRef("data", Key(("missing",)))
        language = ProbeLanguage("data", (
            ProbeValue("data", "broken", (missing,)),
        ))

        with self.assertRaisesRegex(ValueError, "unknown symbol reference"):
            BlueprintLinker(roots=("data",)).link(
                _probe_languages(data=language.values), Namespace(),
            )

    def test_a_reference_cycle_is_refused(self) -> None:
        first = SymbolRef("data", Key(("first",)))
        second = SymbolRef("data", Key(("second",)))
        language = ProbeLanguage("data", (
            ProbeValue("data", "first", (second,)),
            ProbeValue("data", "second", (first,)),
        ))

        with self.assertRaisesRegex(ValueError, "symbol reference cycle"):
            BlueprintLinker(roots=("data",)).link(
                _probe_languages(data=language.values), Namespace(),
            )

    def test_a_binding_reference_must_exist(self) -> None:
        missing = SymbolRef("topology", Key(("missing",)))
        language = ProbeLanguage("binding", (
            ProbeValue("binding", "broken", (missing,)),
        ))

        with self.assertRaisesRegex(ValueError, "unknown symbol reference"):
            BlueprintLinker(roots=("binding",)).link(
                _probe_languages(binding=language.values), Namespace(),
            )

    def test_the_root_closure_is_selected_before_transcription(self) -> None:
        keep = SymbolRef("data", Key(("keep",)))
        dependency = SymbolRef("data", Key(("dependency",)))
        data = ProbeLanguage("data", (
            ProbeValue("data", "keep", (dependency,)),
            ProbeValue("data", "dependency"),
            ProbeValue("data", "orphan"),
        ))
        binding = ProbeLanguage("binding", (
            ProbeValue("binding", "root", (keep,)),
        ))

        BlueprintLinker(roots=("binding",)).link(
            (
                ProbeLanguage("expressions"), ProbeLanguage("asset"),
                data, ProbeLanguage("topology"), binding,
            ),
            Namespace(),
        )

        self.assertEqual(data.transcribed, ["dependency", "keep"])
        self.assertEqual(binding.transcribed, ["root"])

    def test_default_roots_include_every_declaration(self) -> None:
        data = ProbeLanguage("data", (
            ProbeValue("data", "kept"),
            ProbeValue("data", "orphan"),
        ))

        BlueprintLinker().link(
            (
                ProbeLanguage("expressions"), ProbeLanguage("asset"),
                data, ProbeLanguage("topology"),
                ProbeLanguage("binding"),
            ),
            Namespace(),
        )

        self.assertEqual(data.transcribed, ["kept", "orphan"])

    def test_a_batch_implementation_satisfies_the_same_contract(self) -> None:
        data = BatchProbeLanguage("data", (
            ProbeValue("data", "first"), ProbeValue("data", "second"),
        ))
        languages = (
            ProbeLanguage("expressions"),
            ProbeLanguage("asset"),
            data,
            ProbeLanguage("topology"),
            ProbeLanguage("binding"),
        )

        BlueprintLinker(roots=("data",)).link(languages, Namespace())

        self.assertEqual(data.transcribed, ["first", "second"])


class DataSymbolKeyTests(unittest.TestCase):
    def test_a_unique_struct_uses_its_graph_name(self) -> None:
        class Info(Struct):
            options = StructOptions(name="info")
            value: Field[str] = field()

        language = DataLanguage()
        (declaration,) = _data_declarations(language, Namespace(Info))

        self.assertEqual(language.compute_key(declaration), Key(("info",)))
        self.assertEqual(
            language.get_identity(Info),
            SymbolRef("data", Key(("info",))),
        )

    def test_a_repeated_struct_uses_its_qualified_name(self) -> None:
        class Info(Struct):
            options = StructOptions(name="info")
            value: Field[str] = field()

        class OtherInfo(Struct):
            options = StructOptions(name="info")
            other: Field[str] = field()

        language = DataLanguage()
        declarations = _data_declarations(
            language, Namespace(Info, OtherInfo),
        )
        keys = {language.compute_key(item) for item in declarations}

        self.assertEqual(len(keys), 2)
        self.assertTrue(all(key.segments[0] == "info" for key in keys))

    def test_a_struct_name_colliding_with_a_relation_is_qualified(self) -> None:
        class Go(Struct):
            options = StructOptions(name="go")
            value: Field[str] = field()

        class GoTable(Table[TestEstate]):
            options = TableOptions(name="go")
            value: Field[str] = field()

        language = DataLanguage()
        declarations = _data_declarations(
            language, Namespace(Go, GoTable),
        )
        keys = {
            language.get_kind(item): language.compute_key(item)
            for item in declarations
        }

        self.assertEqual(keys["relation"], Key(("go",)))
        self.assertEqual(keys["struct"].segments[0], "go")
        self.assertEqual(len(keys["struct"].segments), 2)

    def test_a_table_without_an_asset_is_refused(self) -> None:
        with self.assertRaisesRegex(TypeError, "Table\\[Asset\\]"):
            class NoAsset(Table):
                value: Field[str] = field()


class AuthoringReferenceTests(unittest.TestCase):
    def test_data_references_read_the_authoring_declaration(self) -> None:
        class Row(Table[TestEstate]):
            options = TableOptions(name="row")
            value: Field[int] = field(name="value")

        language = DataLanguage()
        declarations = language.discover_declarations(Namespace(Row))
        relation = next(
            declaration for declaration in declarations
            if declaration.value is Row
        )
        references = language.get_references(relation.value, None)

        self.assertIn(
            SymbolRef("data", Key(("row.value",))), references,
        )
        self.assertIn(
            SymbolRef("asset", Key(("estate",))), references,
        )


if __name__ == "__main__":
    unittest.main()
