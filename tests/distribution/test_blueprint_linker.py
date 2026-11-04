from __future__ import annotations

import unittest

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
    Symbol,
    SymbolRef,
)
from kg_build_system.distribution.interpreter.service._private.link import (
    select_reachable,
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


class BrokenDataLanguage:
    name = "data"

    def discover_declarations(self, namespace):
        del namespace
        return (Declaration("broken"),)

    def compute_key(self, declaration):
        del declaration
        return Key(("broken",))

    def get_kind(self, declaration):
        del declaration
        return "struct"

    def owns(self, value):
        return False

    def get_identity(self, value):
        del value
        return None

    def get_references(self, value, resolver):
        del value, resolver
        return ()

    def transcribe_many(self, declarations, context):
        del declarations, context
        reference = SymbolRef("data", Key(("broken",)))
        return {
            reference: Symbol(
                reference.key,
                "struct",
                StructDTO("broken", ()),
                (SymbolRef("data", Key(("missing",))),),
            ),
        }


class StructOnlyDataLanguage(BrokenDataLanguage):
    def transcribe_many(self, declarations, context):
        del declarations, context
        reference = SymbolRef("data", Key(("broken",)))
        return {
            reference: Symbol(
                reference.key, "struct", StructDTO("broken", ()),
            ),
        }


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

    def test_languages_are_transcribed_in_dependency_order(self) -> None:
        calls: list[str] = []

        class RecordingExpressions(ExpressionsLanguage):
            def transcribe_many(self, declarations, context):
                calls.append("expressions")
                return super().transcribe_many(declarations, context)

        class RecordingAsset(AssetLanguage):
            def transcribe_many(self, declarations, context):
                calls.append("asset")
                return super().transcribe_many(declarations, context)

        class RecordingData(DataLanguage):
            def transcribe_many(self, declarations, context):
                calls.append("data")
                return super().transcribe_many(declarations, context)

        class RecordingTopology(TopologyLanguage):
            def transcribe_many(self, declarations, context):
                calls.append("topology")
                return super().transcribe_many(declarations, context)

        class RecordingBinding(BindingLanguage):
            def transcribe_many(self, declarations, context):
                calls.append("binding")
                return super().transcribe_many(declarations, context)

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
        class DuplicateData(StructOnlyDataLanguage):
            def discover_declarations(self, namespace):
                del namespace
                return (Declaration("one"), Declaration("two"))

            def compute_key(self, declaration):
                del declaration
                return Key(("same",))

        with self.assertRaisesRegex(ValueError, "declares key same twice"):
            BlueprintLinker().link(
                (
                    DuplicateData(), AssetLanguage(), TopologyLanguage(),
                    BindingLanguage(), ExpressionsLanguage(),
                ),
                Namespace(),
            )

    def test_a_fake_language_produces_symbols_for_the_blueprint(self) -> None:
        linked = BlueprintLinker().link(
            (
                StructOnlyDataLanguage(), AssetLanguage(), TopologyLanguage(),
                BindingLanguage(), ExpressionsLanguage(),
            ),
            Namespace(),
        )

        self.assertEqual(
            linked.data.structs, (StructDTO("broken", ()),),
        )

    def test_a_missing_symbol_reference_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown symbol reference"):
            BlueprintLinker().link(
                (
                    BrokenDataLanguage(), AssetLanguage(), TopologyLanguage(),
                    BindingLanguage(), ExpressionsLanguage(),
                ),
                Namespace(),
            )

    def test_a_binding_reference_must_exist(self) -> None:
        class BrokenBindingLanguage(BindingLanguage):
            def transcribe_many(self, declarations, context):
                del declarations, context
                reference = SymbolRef("binding", Key(("broken",)))
                return {
                    reference: Symbol(
                        reference.key,
                        "binding",
                        object(),
                        (SymbolRef("topology", Key(("missing",))),),
                    ),
                }

        with self.assertRaisesRegex(ValueError, "unknown symbol reference"):
            BlueprintLinker().link(
                (
                    DataLanguage(), AssetLanguage(), TopologyLanguage(),
                    BrokenBindingLanguage(), ExpressionsLanguage(),
                ),
                Namespace(),
            )


class DataSymbolKeyTests(unittest.TestCase):
    def test_a_unique_struct_uses_its_graph_name(self) -> None:
        class Info(Struct):
            options = StructOptions(name="info")
            value: Field[str] = field()

        language = DataLanguage()
        (declaration,) = tuple(
            language.discover_declarations(Namespace(Info))
        )

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
        declarations = tuple(
            language.discover_declarations(Namespace(Info, OtherInfo))
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
        declarations = tuple(
            language.discover_declarations(Namespace(Go, GoTable))
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


class RootPolicyTests(unittest.TestCase):
    def test_only_reachable_symbols_are_selected(self) -> None:
        node = SymbolRef("topology", Key(("site",)))
        binding = SymbolRef("binding", Key(("site",)))
        orphan = SymbolRef("topology", Key(("orphan",)))
        symbols = {
            node: Symbol(Key(("site",)), "node", object()),
            binding: Symbol(
                Key(("site",)), "binding", object(), (node,),
            ),
            orphan: Symbol(Key(("orphan",)), "node", object()),
        }

        selected = select_reachable(symbols, ("binding",))

        self.assertEqual(set(selected), {binding, node})


if __name__ == "__main__":
    unittest.main()
