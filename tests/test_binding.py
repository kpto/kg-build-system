"""Tests for class-based binding declarations."""

import unittest

from demo.binding import BINDINGS
from kg_build_system.binding import (
    BindingSet,
    EdgeBindingDefinition,
    FieldMapping,
    InputFormat,
    NodeBindingDefinition,
    Column,
    Table,
)


class BindingTests(unittest.TestCase):
    def test_portable_schema_and_binding_models_serialize(self) -> None:
        table = Table(
            name="Rows",
            location="rows.csv",
            format=InputFormat.CSV,
            columns=(Column(name="id", python_type="str", nullable=False),),
        )
        node_binding = NodeBindingDefinition(
            target="Thing",
            table=table,
            mappings=(FieldMapping(target="identifier", source="id"),),
        )
        edge_binding = EdgeBindingDefinition(
            target="RelatesTo",
            table=table,
            source="id",
            target_endpoint="id",
            mappings=(),
        )

        bindings = BindingSet("Example", node_bindings=(node_binding,), edge_bindings=(edge_binding,))

        self.assertEqual(bindings.to_dict()["node_bindings"][0]["table"]["columns"][0]["name"], "id")
        self.assertEqual(bindings.to_dict()["edge_bindings"][0]["kind"], "edge")

    def test_demo_bindings_serialize(self) -> None:
        definition = BINDINGS.to_dict()

        self.assertEqual(definition["name"], "target_disease_demo")
        self.assertEqual(definition["node_bindings"][0]["target"], "Target")
        self.assertEqual(definition["node_bindings"][0]["mappings"][0]["target"], "identifier")
        self.assertEqual(definition["edge_bindings"][0]["source"], "target_id")
        self.assertEqual(definition["edge_bindings"][0]["mappings"][0]["target"], "property:score")
