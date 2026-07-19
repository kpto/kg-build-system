"""Tests for class-based binding declarations."""

import unittest

from demo.binding import BINDINGS


class BindingTests(unittest.TestCase):
    def test_demo_bindings_serialize(self) -> None:
        definition = BINDINGS.to_dict()

        self.assertEqual(definition["name"], "target_disease_demo")
        self.assertEqual(definition["node_bindings"][0]["target"], "Target")
        self.assertEqual(definition["node_bindings"][0]["mappings"][0]["target"], "identifier")
        self.assertEqual(definition["edge_bindings"][0]["source"], "target_id")
        self.assertEqual(definition["edge_bindings"][0]["mappings"][0]["target"], "property:score")
