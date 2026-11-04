from __future__ import annotations

import unittest

from kg_build_system import (
    Field,
    Node,
    NodeValues,
    PropertySlot,
    Table,
    TableOptions,
    field,
    node_binding,
    property,
)
from kg_build_system.distribution.interpreter import GraphBlueprint, create_blueprint
from kg_build_system.distribution.interpreter.service.internal import (
    blueprint_from_document,
    blueprint_to_document,
)
from kg_build_system.distribution.languages.binding.model.internal import (
    NodeBindingDTO,
)
from kg_build_system.distribution.languages.binding.service.internal import (
    BindingLanguage,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ColumnDTO,
    DataPartDTO,
    RelationDTO,
    SourceDTO,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    FieldReferenceDTO,
    LiteralExpressionDTO,
    OperationExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    expression_from_document,
    expression_to_document,
)
from kg_build_system.distribution.languages.topology.model.internal import (
    EdgeDTO,
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
)
from kg_build_system.distribution.model.public.refs import (
    EdgeRef,
    FieldRef,
    NodeRef,
    OperationRef,
    PropertyRef,
    RelationRef,
    SourceRef,
    ref_from_document,
)
from kg_build_system.kernel import Key, SymbolRef
from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO


def _site() -> NodeRef:
    return NodeRef("topology", Key(("site",)))


def _unit() -> NodeRef:
    return NodeRef("topology", Key(("unit",)))


class ReferenceRoleTests(unittest.TestCase):
    def test_every_role_round_trips_its_document(self) -> None:
        cases = (
            (NodeRef, Key(("site",))),
            (EdgeRef, Key(("has_unit",))),
            (RelationRef, Key(("sites",))),
            (FieldRef, Key(("sites.site_name",))),
            (PropertyRef, Key(("site.name",))),
            (SourceRef, Key(("sites", "source"))),
            (OperationRef, Key(("default_to",))),
        )
        for role_type, key in cases:
            with self.subTest(role=role_type.__name__):
                reference = role_type("language", key)
                document = reference.to_document()
                self.assertEqual(document[0], "language")
                self.assertEqual(document[1], role_type.role)
                restored = ref_from_document(document)
                self.assertIs(type(restored), role_type)
                self.assertEqual(restored, reference)

    def test_a_reference_can_wrap_a_symbol_reference(self) -> None:
        symbol = SymbolRef("data", Key(("sites.site_name",)))

        reference = FieldRef(symbol)

        self.assertIs(reference.symbol, symbol)
        self.assertEqual(reference.key, Key(("sites.site_name",)))
        self.assertEqual(reference.name, "sites.site_name")
        self.assertEqual(reference.relation, "sites")
        self.assertEqual(reference.field, "site_name")
        self.assertEqual(reference, FieldRef(symbol))
        self.assertEqual(hash(reference), hash(FieldRef(symbol)))

    def test_property_and_source_roles_split_their_key(self) -> None:
        prop = PropertyRef("topology", Key(("site.name",)))
        source = SourceRef("data", Key(("sites", "source")))

        self.assertEqual((prop.component, prop.property), ("site", "name"))
        self.assertEqual(source.relation, "sites")


class ExpressionReferenceDocumentTests(unittest.TestCase):
    def test_an_expression_document_names_its_field_and_operation(self) -> None:
        read = FieldReferenceDTO(
            logical_type=UnitTypeDTO("str"),
            field=FieldRef("data", Key(("sites.site_name",))),
            path=(),
        )
        operation = OperationExpressionDTO(
            logical_type=UnitTypeDTO("str"),
            operator=OperationRef("expressions", Key(("default_to",))),
            arguments=(read,),
        )

        document = expression_to_document(operation)

        self.assertEqual(
            document["operator"],
            ["expressions", "operation", "default_to"],
        )
        self.assertEqual(
            document["arguments"][0]["field"],
            ["data", "field", "sites.site_name"],
        )
        self.assertEqual(expression_from_document(document), operation)


class BlueprintReferenceCodecTests(unittest.TestCase):
    def test_the_blueprint_round_trips_typed_references(self) -> None:
        site = NodeDTO(
            "site",
            labels=("Site",),
            properties=(
                PropertyDTO(
                    "name",
                    UnitTypeDTO("str"),
                    PropertyRef("topology", Key(("site.name",))),
                ),
            ),
            parent=NodeRef("topology", Key(("entity",))),
        )
        entity = NodeDTO("entity", abstract=True)
        unit = NodeDTO("unit", labels=("Unit",))
        edge = EdgeDTO(
            "has_unit",
            ("HAS_UNIT",),
            source=_site(),
            target=_unit(),
        )
        relation = RelationDTO(
            "sites",
            (
                ColumnDTO(
                    "site_name",
                    UnitTypeDTO("str"),
                    FieldRef("data", Key(("sites.site_name",))),
                ),
            ),
        )
        source = SourceDTO(
            relation=RelationRef("data", Key(("sites",))),
            location="sites.csv",
            format="csv",
        )
        binding = NodeBindingDTO(
            _site(),
            LiteralExpressionDTO(
                logical_type=UnitTypeDTO("str"), value="site::",
            ),
            properties=((
                "name",
                FieldReferenceDTO(
                    logical_type=UnitTypeDTO("str"),
                    field=FieldRef("data", Key(("sites.site_name",))),
                    path=(),
                ),
            ),),
        )
        blueprint = GraphBlueprint(
            graph=GraphPartDTO(nodes=(entity, site, unit), edges=(edge,)),
            data=DataPartDTO(
                structs=(),
                relations=(relation,),
                projections=(),
                sources=(source,),
            ),
            bindings=(binding,),
            sources=(source,),
        )

        document = blueprint_to_document(blueprint)
        restored = blueprint_from_document(document)

        self.assertEqual(restored, blueprint)
        self.assertEqual(
            document["graph"]["edges"][0]["source"],
            ["topology", "node", "site"],
        )
        self.assertEqual(
            document["data"]["relations"][0]["columns"][0]["ref"],
            ["data", "field", "sites.site_name"],
        )
        self.assertEqual(
            document["data"]["sources"][0]["relation"],
            ["data", "relation", "sites"],
        )
        self.assertEqual(
            document["bindings"][0]["node"],
            ["topology", "node", "site"],
        )


class BindingSymbolReferenceTests(unittest.TestCase):
    def test_a_binding_references_a_field_and_an_operation_symbol(self) -> None:
        class Row(Table):
            options = TableOptions(name="row")
            value: Field[int] = field(name="value")

        class Item(Node):
            value: PropertySlot[int] = property()

        binding = node_binding(
            target=Item,
            rows=Row.row_source(),
            bind=lambda row: NodeValues(
                build_key=row.value.expression,
                properties=Item(value=row.value.expression.add(1)),
            ),
        )

        blueprint = create_blueprint(bindings=(binding,))

        self.assertEqual(
            BindingLanguage().get_references(blueprint.bindings[0], None),
            (
                SymbolRef("topology", Key(("item",))),
                SymbolRef("data", Key(("row",))),
                SymbolRef("data", Key(("row.value",))),
                SymbolRef("expressions", Key(("add",))),
            ),
        )


if __name__ == "__main__":
    unittest.main()
