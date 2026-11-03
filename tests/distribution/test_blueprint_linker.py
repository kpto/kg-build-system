from __future__ import annotations

import unittest

from kg_build_system.distribution.interpreter import GraphBlueprint
from kg_build_system.distribution.interpreter.service.internal import (
    BlueprintLinker,
    assemble_blueprint,
    validate_blueprint,
)
from kg_build_system.distribution.languages.table.model.internal import DataPartDTO
from kg_build_system.distribution.languages.topology.model.internal import GraphPartDTO
from kg_build_system.kernel import Layer


def _layers() -> dict[str, Layer]:
    return {
        "data": Layer(
            "data",
            DataPartDTO(structs=(), relations=(), projections=(), sources=()),
        ),
        "topology": Layer("topology", GraphPartDTO()),
        "binding": Layer("binding", ()),
    }


class BlueprintLinkerTests(unittest.TestCase):
    def test_requires_the_three_blueprint_layers(self) -> None:
        self.assertEqual(
            BlueprintLinker.requires, ("data", "topology", "binding"),
        )

    def test_linking_returns_the_assembled_and_validated_blueprint(self) -> None:
        layers = _layers()
        expected = assemble_blueprint(
            layers["topology"].value,
            layers["data"].value,
            layers["binding"].value,
        )
        validate_blueprint(expected)

        linked = BlueprintLinker().link(layers)

        self.assertIsInstance(linked, GraphBlueprint)
        self.assertEqual(linked, expected)

    def test_a_missing_layer_raises(self) -> None:
        layers = _layers()
        del layers["binding"]

        with self.assertRaises(KeyError):
            BlueprintLinker().link(layers)


if __name__ == "__main__":
    unittest.main()
