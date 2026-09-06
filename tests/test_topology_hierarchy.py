from __future__ import annotations

import json
import unittest
from dataclasses import dataclass, replace

from kg_build_system import (
    AbstractEdge, AbstractNode, DataSourceConfig, Edge, EdgeOptions,
    EdgeOptionsTemplate, EdgeTemplate, EdgeLabel, Field, InputFormat, Node,
    NodeOptions, NodeOptionsTemplate, NodeTemplate, PropertySlot, Table,
    bind_source, create_blueprint, edge_binding, endpoint, field, node_binding,
    property,
)
from kg_build_system.annotations import Annotation, NodeLabel
from kg_build_system.compile.codec import blueprint_json, decode_blueprint
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.compile.validation import validate_blueprint


@dataclass(frozen=True)
class Trace(Annotation):
    namespace = "topology_hierarchy_test"
    annotation_id = "trace"
    track: str


class Traced(NodeTemplate):
    """Node-side template sharing a provenance concern."""

    options = NodeOptionsTemplate(annotations=(Trace(track="node"),))
    revision: PropertySlot[str] = property()


class Entity(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Entity"),))
    title: PropertySlot[str] = property()


class Item(Traced, Entity, Node):
    code: PropertySlot[str] = property()


class Orphan(Entity, Node):
    label: PropertySlot[str] = property()


class Plain(Node):
    name: PropertySlot[str] = property()


class SourcedEdge(EdgeTemplate):
    options = EdgeOptionsTemplate(annotations=(Trace(track="edge"),))


class Links(SourcedEdge, AbstractEdge[Entity, Entity]):
    options = EdgeOptions(annotations=(EdgeLabel("LINKS"),))


class LinksItem(Links, Edge[Entity, Item]):
    """Descended edge with the target category narrowed."""


class Direct(Edge[Item, Plain]):
    pass


class HierarchyInput(Table):
    identifier: Field[str] = field()
    title: Field[str] = field()
    code: Field[str] = field()
    name: Field[str] = field()
    revision: Field[str] = field()
    label: Field[str] = field()


def _source():
    return bind_source(
        target=HierarchyInput,
        config=DataSourceConfig("hierarchy.json", format=InputFormat.JSON),
    )


def _item_binding():
    return node_binding(
        target=Item,
        build_key=HierarchyInput.identifier.expression.prepend("item::"),
        properties=Item(
            title=HierarchyInput.title,
            code=HierarchyInput.code,
            revision=HierarchyInput.revision,
        ),
    )


def _orphan_binding():
    return node_binding(
        target=Orphan,
        build_key=HierarchyInput.identifier.expression.prepend("orphan::"),
        properties=Orphan(title=HierarchyInput.title, label=HierarchyInput.label),
    )


def _plain_binding():
    return node_binding(
        target=Plain,
        build_key=HierarchyInput.name,
        properties=Plain(name=HierarchyInput.name),
    )


def _links_item_binding(source_node=None):
    return edge_binding(
        target=LinksItem,
        source_node=endpoint(Item) if source_node is None else source_node,
        build_key=HierarchyInput.identifier.expression.prepend("links::"),
        source_build_key=HierarchyInput.identifier.expression.prepend("item::"),
        target_build_key=HierarchyInput.code.expression.prepend("item::"),
        properties=LinksItem(),
    )


def _blueprint(bindings, **overrides) -> BuildBlueprint:
    result = create_blueprint(
        bindings=bindings, sources=(_source(),), modules=(), **overrides
    )
    return result


class NamingTests(unittest.TestCase):
    def test_tier_suffixes_strip_from_inferred_names(self) -> None:
        class TracedAbstractNode(AbstractNode): ...
        class LegacyNode(AbstractNode): ...

        class Widget(AbstractNode): ...

        class PairAbstractEdge(AbstractEdge[Entity, Entity]): ...
        class LegacyEdge(AbstractEdge[Entity, Entity]): ...

        class PlainTracedNode(TracedAbstractNode, Node): ...
        class Explicit(AbstractNode):
            options = NodeOptions(name="Chosen Name")

        self.assertEqual(TracedAbstractNode._component_name, "traced")
        self.assertEqual(LegacyNode._component_name, "legacy")
        self.assertEqual(Widget._component_name, "widget")
        self.assertEqual(PairAbstractEdge._component_name, "pair")
        self.assertEqual(LegacyEdge._component_name, "legacy")
        self.assertEqual(PlainTracedNode._component_name, "plain_traced")
        self.assertEqual(Explicit._component_name, "Chosen Name")


class TierTests(unittest.TestCase):
    def test_template_is_inert(self) -> None:
        self.assertIsNone(vars(Traced).get("_component_declaration_kind"))
        self.assertEqual(Traced._template_annotations, (Trace(track="node"),))
        self.assertIsNone(vars(SourcedEdge).get("_component_declaration_kind"))

    def test_category_is_abstract_and_concrete_records_parent(self) -> None:
        self.assertTrue(Entity._component_abstract)
        self.assertEqual(Entity._component_declaration_kind, "node")
        self.assertFalse(Item._component_abstract)
        self.assertIs(Item._component_parent_class, Entity)
        self.assertEqual(
            (Item._component_name, Entity._component_name), ("item", "entity")
        )
        self.assertTrue(Links._component_abstract)
        self.assertFalse(LinksItem._component_abstract)
        self.assertIs(LinksItem._component_parent_class, Links)
        self.assertEqual(LinksItem._component_name, "links_item")

    def test_concrete_components_are_terminal(self) -> None:
        with self.assertRaisesRegex(TypeError, "cannot inherit from concrete"):
            class Copy(Item, Node): ...

    def test_two_categories_fail_at_the_diamond(self) -> None:
        class Second(AbstractNode): ...
        with self.assertRaisesRegex(TypeError, "more than one abstract category"):
            class Both(Entity, Second, Node): ...

    def test_non_framework_base_is_rejected(self) -> None:
        class Foreign: ...
        with self.assertRaisesRegex(TypeError, "non-framework base"):
            class Mixed(Foreign, Node): ...

    def test_cross_kind_lineage_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "cannot mix node-side and edge-side"):
            class Weird(Traced, AbstractEdge[Entity, Entity]): ...
        with self.assertRaisesRegex(TypeError, "cannot mix node-side and edge-side"):
            class Nasty(Item, Direct): ...

    def test_direct_root_inheritance_is_rejected(self) -> None:
        from kg_build_system.topology.models import _TopologyDeclarationBase

        with self.assertRaisesRegex(TypeError, "must inherit from"):
            class Bare(_TopologyDeclarationBase): ...


class OptionsTierTests(unittest.TestCase):
    def test_template_given_real_options_is_redirected(self) -> None:
        with self.assertRaisesRegex(TypeError, "wrap it"):
            class Wrong(Traced):
                options = NodeOptions(name="identity")

    def test_template_given_cross_kind_options_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "not NodeOptionsTemplate"):
            class Cross(SourcedEdge):
                options = NodeOptionsTemplate()

    def test_template_given_unwrapped_sequence_is_redirected(self) -> None:
        with self.assertRaisesRegex(TypeError, "wrap the value"):
            class Raw(Traced):
                options = (Trace(track="raw"),)

    def test_ir_class_given_template_options_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "declare NodeOptions, not template"):
            class Mislabeled(Entity, Node):
                options = NodeOptionsTemplate()

    def test_kind_mismatched_options_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be a NodeOptions value"):
            class WrongKind(Entity, Node):
                options = EdgeOptions()

    def test_effective_annotations_flow_only_from_templates(self) -> None:
        self.assertEqual(Item._component_annotations, (Trace(track="node"),))
        self.assertEqual(Entity._component_annotations, (NodeLabel("Entity"),))
        self.assertEqual(
            Links._component_annotations, (Trace(track="edge"), EdgeLabel("LINKS"))
        )
        self.assertEqual(LinksItem._component_annotations, (Trace(track="edge"),))
        self.assertEqual(Orphan._component_annotations, ())

    def test_description_is_own_only(self) -> None:
        self.assertIsNone(Entity._metadata.get("description"))
        self.assertIsNone(Item._metadata.get("description"))

        class Documented(Entity, Node):
            """Own docstring."""

            extra: PropertySlot[str] = property()

        self.assertEqual(Documented._metadata.get("description"), "Own docstring.")

    def test_options_description_wins_over_docstring(self) -> None:
        class Described(Entity, Node):
            """Ignored docstring."""

            options = NodeOptions(description="Explicit.")
            extra: PropertySlot[str] = property()

        self.assertEqual(Described._metadata.get("description"), "Explicit.")

    def test_label_uniqueness_against_the_effective_set(self) -> None:
        with self.assertRaisesRegex(TypeError, "node labels"):
            class Double(Entity, Node):
                options = NodeOptions(annotations=(NodeLabel("A"), NodeLabel("B")))

        class LabelledTemplate(NodeTemplate):
            options = NodeOptionsTemplate(annotations=(NodeLabel("FromTemplate"),))

        with self.assertRaisesRegex(TypeError, "node labels"):
            class Clashing(LabelledTemplate, Entity, Node):
                options = NodeOptions(annotations=(NodeLabel("Own"),))


class EndpointDescentTests(unittest.TestCase):
    def test_declared_endpoints_are_recorded(self) -> None:
        self.assertEqual(
            (Links._metadata["source"], Links._metadata["target"]), (Entity, Entity)
        )
        self.assertEqual(
            (LinksItem._metadata["source"], LinksItem._metadata["target"]),
            (Entity, Item),
        )

    def test_widened_endpoint_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "equal or descend"):
            class Widened(Links, Edge[Entity, Plain]): ...

    def test_endpoints_are_inherited_and_may_be_narrowed(self) -> None:
        class Leaf(Links): ...
        self.assertTrue(Leaf._component_abstract)
        self.assertIs(Leaf._component_parent_class, Links)
        self.assertIs(Leaf._metadata["source"], Entity)
        self.assertIs(Leaf._metadata["target"], Entity)

        class Narrowed(Links, AbstractEdge[Entity, Item]): ...
        self.assertTrue(Narrowed._component_abstract)
        self.assertIs(Narrowed._metadata["target"], Item)

        # a concrete child under the bare abstract child inherits the
        # lineage through it and may narrow
        class LeafChild(Leaf, Edge[Entity, Item]): ...
        self.assertFalse(LeafChild._component_abstract)
        self.assertIs(LeafChild._component_parent_class, Leaf)
        self.assertIs(LeafChild._metadata["target"], Item)

        # a bare terminal base keeps the parent's endpoints unchanged
        class Untouched(Links, Edge): ...
        self.assertFalse(Untouched._component_abstract)
        self.assertIs(Untouched._metadata["source"], Entity)
        self.assertIs(Untouched._metadata["target"], Entity)

        with self.assertRaisesRegex(TypeError, "equal or descend"):
            class Widened(Leaf, Edge[Entity, Plain]): ...

    def test_endpoints_must_be_declared_or_inherited(self) -> None:
        with self.assertRaisesRegex(TypeError, "must declare its edge endpoints"):
            class Undeclared(AbstractEdge): ...

    def test_endpoint_categories_are_node_side(self) -> None:
        with self.assertRaisesRegex(TypeError, "not node-side"):
            class Bypassed(Edge[Links, Item]): ...
        with self.assertRaisesRegex(TypeError, "not a node declaration"):
            class Rooted(Edge[Entity, Node]): ...
        import types

        with self.assertRaisesRegex(TypeError, "not node-side"):
            types.new_class("Detoured", (AbstractEdge[Links, Item],), {})

    def test_descent_guard_is_base_order_insensitive(self) -> None:
        class Flipped(Edge[Entity, Item], Links): ...
        self.assertIs(Flipped._metadata["target"], Item)


class EndpointTokenTests(unittest.TestCase):
    def test_endpoint_names_a_concrete_node(self) -> None:
        self.assertIs(endpoint(Item).target, Item)

    def test_abstract_and_non_node_targets_are_rejected(self) -> None:
        for target in (Entity, Traced, "not-a-node"):
            with self.assertRaisesRegex(TypeError, "is not a concrete node"):
                endpoint(target)  # type: ignore[arg-type]


class EdgeBindingFactoryTests(unittest.TestCase):
    def test_concrete_endpoints_default_to_the_declaration(self) -> None:
        binding = edge_binding(
            target=Direct,
            build_key=HierarchyInput.identifier,
            source_build_key=HierarchyInput.identifier,
            target_build_key=HierarchyInput.code,
            properties=Direct(),
        )
        self.assertIsNone(binding.source_node)
        self.assertIsNone(binding.target_node)

    def test_explicit_tokens_naming_declared_concrete_endpoints_stay_valid(self) -> None:
        binding = edge_binding(
            target=Direct,
            source_node=endpoint(Item),
            target_node=endpoint(Plain),
            build_key=HierarchyInput.identifier,
            source_build_key=HierarchyInput.identifier,
            target_build_key=HierarchyInput.code,
            properties=Direct(),
        )
        self.assertIs(binding.source_node, Item)
        self.assertIs(binding.target_node, Plain)

    def test_tokens_are_recorded_for_category_sides(self) -> None:
        binding = _links_item_binding()
        self.assertIs(binding.source_node, Item)
        self.assertIsNone(binding.target_node)

    def test_missing_token_for_abstract_side_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must name the declared endpoint category"):
            edge_binding(
                target=LinksItem,
                build_key=HierarchyInput.identifier,
                source_build_key=HierarchyInput.identifier,
                target_build_key=HierarchyInput.code,
                properties=LinksItem(),
            )

    def test_token_outside_the_category_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "equal or descend"):
            edge_binding(
                target=LinksItem,
                source_node=endpoint(Plain),
                build_key=HierarchyInput.identifier,
                source_build_key=HierarchyInput.identifier,
                target_build_key=HierarchyInput.code,
                properties=LinksItem(),
            )

    def test_raw_class_is_rejected_where_a_token_is_required(self) -> None:
        with self.assertRaisesRegex(TypeError, r"must be an endpoint\(\.\.\.\) token"):
            edge_binding(
                target=LinksItem,
                source_node=Item,  # type: ignore[arg-type]
                build_key=HierarchyInput.identifier,
                source_build_key=HierarchyInput.identifier,
                target_build_key=HierarchyInput.code,
                properties=LinksItem(),
            )

    def test_abstract_targets_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "concrete node"):
            node_binding(
                target=Entity,  # type: ignore[arg-type]
                build_key=HierarchyInput.identifier,
                properties=None,  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(TypeError, "concrete edge"):
            edge_binding(
                target=Links,  # type: ignore[arg-type]
                build_key=HierarchyInput.identifier,
                source_build_key=HierarchyInput.identifier,
                target_build_key=HierarchyInput.code,
                properties=None,  # type: ignore[arg-type]
            )


class BlueprintTests(unittest.TestCase):
    def blueprint(self) -> BuildBlueprint:
        return _blueprint((_item_binding(), _links_item_binding()))

    def test_component_closure_includes_abstract_chains(self) -> None:
        result = self.blueprint()
        self.assertEqual(
            {item.name for item in result.components},
            {"entity", "item", "links", "links_item"},
        )
        components = {item.name: item for item in result.components}
        self.assertTrue(components["entity"].abstract)
        self.assertTrue(components["links"].abstract)
        self.assertFalse(components["item"].abstract)
        self.assertIsNone(components["entity"].parent)
        self.assertEqual(components["item"].parent, components["entity"].symbol_id)
        self.assertEqual(components["links_item"].parent, components["links"].symbol_id)
        self.assertEqual(components["links"].source, "entity")
        self.assertEqual(components["links_item"].source, "entity")
        self.assertEqual(components["links_item"].target, "item")

    def test_binding_records_supplied_endpoints(self) -> None:
        binding = next(item for item in self.blueprint().bindings if item.kind == "edge")
        self.assertEqual(binding.source_node, "item")
        self.assertIsNone(binding.target_node)

    def test_endpoint_tokens_distinguish_otherwise_identical_bindings(self) -> None:
        combined = _blueprint((
            _item_binding(), _orphan_binding(),
            _links_item_binding(),
            _links_item_binding(source_node=endpoint(Orphan)),
        ))
        edge_symbols = {
            item.symbol_id for item in combined.bindings if item.kind == "edge"
        }
        self.assertEqual(len(edge_symbols), 2, edge_symbols)

    def test_codec_round_trips_the_new_fields(self) -> None:
        result = self.blueprint()
        encoded = blueprint_json(result)
        self.assertEqual(decode_blueprint(json.loads(encoded)), result)
        self.assertEqual(result.schema_version, 4)
        document = json.loads(encoded)
        self.assertEqual(document["schema_version"], 4)
        self.assertTrue(any(item.get("abstract") for item in document["components"]))
        self.assertTrue(
            any(item.get("parent") for item in document["components"])
        )

    def test_multi_level_chain_flows_through_the_blueprint(self) -> None:
        class Chain(Links, AbstractEdge[Entity, Item]):
            """Abstract chain level that narrows the target category."""

        class LeafChild(Chain, Edge[Entity, Item]):
            """Concrete edge under the narrowed chain level."""

        binding = edge_binding(
            target=LeafChild,
            source_node=endpoint(Item),
            build_key=HierarchyInput.identifier.expression.prepend("chain::"),
            source_build_key=HierarchyInput.identifier,
            target_build_key=HierarchyInput.code,
            properties=LeafChild(),
        )
        result = _blueprint((_item_binding(), binding))
        components = {item.name: item for item in result.components}
        by_symbol = {item.symbol_id: item for item in result.components}
        self.assertEqual(
            set(components), {"entity", "item", "links", "chain", "leaf_child"}
        )
        leaf = components["leaf_child"]
        self.assertEqual(leaf.parent, components["chain"].symbol_id)
        self.assertEqual(components["chain"].parent, components["links"].symbol_id)
        self.assertEqual((leaf.source, leaf.target), ("entity", "item"))
        edge_ir = next(item for item in result.bindings if item.kind == "edge")
        self.assertEqual(edge_ir.source_node, "item")
        self.assertIsNone(edge_ir.target_node)
        # every abstract in the chain entered the IR unbound
        self.assertTrue(all(components[name].abstract for name in ("links", "chain")))

    def test_abstract_binding_targets_are_rejected(self) -> None:
        result = self.blueprint()
        node = next(item for item in result.bindings if item.kind == "node")
        with self.assertRaisesRegex(ValueError, "may not target abstract"):
            validate_blueprint(replace(
                result, bindings=(replace(node, component="entity"),)
            ))

    def test_supplied_endpoint_needs_no_producer(self) -> None:
        # Endpoint identity is the component, not a producer: naming an
        # endpoint requires no node binding producing it in this blueprint
        result = _blueprint((
            _item_binding(), _orphan_binding(), _links_item_binding(),
        ))
        edge = next(item for item in result.bindings if item.kind == "edge")
        without_producer = tuple(
            item for item in result.bindings
            if item.kind == "node" and item.component != "orphan"
        )
        validate_blueprint(replace(
            result,
            bindings=(*without_producer, replace(edge, source_node="orphan")),
        ))

    def test_endpoint_must_descend_from_the_declared_category(self) -> None:
        result = _blueprint((
            _item_binding(), _plain_binding(), _links_item_binding(),
        ))
        edge = next(item for item in result.bindings if item.kind == "edge")
        with self.assertRaisesRegex(ValueError, "equal or descend"):
            validate_blueprint(replace(
                result,
                bindings=(
                    *(item for item in result.bindings if item.kind != "edge"),
                    replace(edge, source_node="plain"),
                ),
            ))

    def test_declared_abstract_endpoints_are_fine_unbound(self) -> None:
        # `links` declares the abstract Entity endpoints and no binding
        # names them; the default blueprint carries it and stays valid
        validate_blueprint(self.blueprint())


if __name__ == "__main__":
    unittest.main()

class InheritedSlotOptionalityTests(unittest.TestCase):
    """A slot declared with the null default is optional for its bindings."""

    def test_member_may_leave_the_category_slot_unbound(self) -> None:
        class TermCategory(AbstractNode):
            label: PropertySlot[str | None] = property(default=None)

        class BareTerm(TermCategory, Node):
            name: PropertySlot[str] = property()

        class TermInput(Table):
            identifier: Field[str] = field()
            name: Field[str] = field()

        import tempfile
        from pathlib import Path

        from kg_build_system import build, compile
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "terms.json"
            source_path.write_text(
                json.dumps([{"identifier": "1", "name": "alpha"}]), encoding="utf-8",
            )
            source = bind_source(
                target=TermInput,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=BareTerm,
                build_key=TermInput.identifier,
                properties=BareTerm(name=TermInput.name),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]
            self.assertIsNone(rows[0].get("label"))
            self.assertEqual(rows[0]["name"], "alpha")

    def test_inherited_nullable_slot_without_the_default_is_required(self) -> None:
        class QuietCategory(AbstractNode):
            label: PropertySlot[str | None] = property()

        class QuietMember(QuietCategory, Node):
            name: PropertySlot[str] = property()

        with self.assertRaisesRegex(TypeError, "label"):
            node_binding(
                target=QuietMember,
                build_key=HierarchyInput.identifier,
                properties=QuietMember(name=HierarchyInput.name),
            )

    def test_the_null_default_requires_a_nullable_slot(self) -> None:
        with self.assertRaisesRegex(TypeError, "only when nullable"):
            class Demanding(Node):
                name: PropertySlot[str] = property(default=None)

    def test_non_nullable_category_slot_is_still_required(self) -> None:
        class Titled(AbstractNode):
            title: PropertySlot[str] = property()

        class TitledNode(Titled, Node):
            name: PropertySlot[str] = property()

        with self.assertRaisesRegex(TypeError, "title"):
            node_binding(
                target=TitledNode,
                build_key=HierarchyInput.identifier,
                properties=TitledNode(name=HierarchyInput.name),
            )

    def test_member_own_nullable_slot_is_still_required(self) -> None:
        class Titled(AbstractNode):
            label: PropertySlot[str | None] = property()

        class Own(Titled, Node):
            name: PropertySlot[str] = property()
            note: PropertySlot[str | None] = property()

        with self.assertRaisesRegex(TypeError, "note"):
            node_binding(
                target=Own,
                build_key=HierarchyInput.identifier,
                properties=Own(
                    name=HierarchyInput.name, label=HierarchyInput.title,
                ),
            )

    def test_shadowed_category_slot_becomes_the_member_own_promise(self) -> None:
        class Titled(AbstractNode):
            label: PropertySlot[str | None] = property()

        class Shadowed(Titled, Node):
            name: PropertySlot[str] = property()
            label: PropertySlot[str | None] = property(name="label")

        with self.assertRaisesRegex(TypeError, "label"):
            node_binding(
                target=Shadowed,
                build_key=HierarchyInput.identifier,
                properties=Shadowed(name=HierarchyInput.name),
            )

    def test_edge_member_may_leave_category_slot_unbound(self) -> None:
        class Claim(AbstractEdge[Item, Plain]):
            note: PropertySlot[str | None] = property(default=None)

        class Claimed(Claim, Edge[Item, Plain]):
            pass

        binding = edge_binding(
            target=Claimed,
            build_key=HierarchyInput.identifier,
            source_build_key=HierarchyInput.identifier,
            target_build_key=HierarchyInput.code,
            properties=Claimed(),
        )
        components = {
            item.name: item for item in _blueprint((binding,)).components
        }
        self.assertTrue(components["claim"].abstract)
