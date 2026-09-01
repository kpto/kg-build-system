from __future__ import annotations

import unittest

from kg_build_system._frozen_json import freeze_json
from kg_build_system.annotations.ir import AnnotationIR
from kg_build_system.modules._labels import semantic_label
from kg_build_system.modules.targets.neo4j.module import _annotation_label
from kg_build_system.topology.ir import ComponentIR

_NAMESPACE = "kg_build_system.topology"


def _label_annotation(kind: str, label: str) -> AnnotationIR:
    return AnnotationIR(
        _NAMESPACE,
        "node_label" if kind == "node" else "edge_label",
        freeze_json({"label": label}),
    )


def _component(
    kind: str = "node",
    name: str = "record",
    annotations: tuple[AnnotationIR, ...] = (),
) -> ComponentIR:
    return ComponentIR(
        symbol_id=f"python:{kind}:example:{name}",
        name=name,
        kind=kind,  # type: ignore[arg-type]
        annotations=annotations,
    )


class SemanticLabelTests(unittest.TestCase):
    def test_defaults_to_the_logical_name_without_an_annotation(self) -> None:
        self.assertEqual(semantic_label(_component()), "record")
        self.assertEqual(semantic_label(_component("edge", "contains")), "contains")

    def test_reads_the_declared_label_for_each_kind(self) -> None:
        self.assertEqual(
            semantic_label(_component(
                "node", "record", (_label_annotation("node", "Record"),),
            )),
            "Record",
        )
        self.assertEqual(
            semantic_label(_component(
                "edge", "contains", (_label_annotation("edge", "CONTAINS"),),
            )),
            "CONTAINS",
        )

    def test_rejects_the_opposite_kind_annotation(self) -> None:
        with self.assertRaisesRegex(ValueError, "incompatible EdgeLabel"):
            semantic_label(_component(
                "node", "record", (_label_annotation("edge", "CONTAINS"),),
            ))

    def test_rejects_more_than_one_matching_annotation(self) -> None:
        # Class creation already rejects duplicate labels, so this backstops a
        # blueprint decoded from JSON.
        with self.assertRaisesRegex(ValueError, "at most one NodeLabel"):
            semantic_label(_component("node", "record", (
                _label_annotation("node", "First"),
                _label_annotation("node", "Second"),
            )))

    def test_rejects_malformed_or_blank_label_arguments(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid serialized arguments"):
            semantic_label(_component("node", "record", (
                AnnotationIR(_NAMESPACE, "node_label", freeze_json({"name": "X"})),
            )))
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            semantic_label(_component(
                "node", "record", (_label_annotation("node", "   "),),
            ))


class Neo4jSpecificLabelRuleTests(unittest.TestCase):
    """The extraction must leave the target's own vocabulary rule in place."""

    def test_node_labels_may_not_carry_multiple_labels(self) -> None:
        with self.assertRaisesRegex(ValueError, "single Neo4j label"):
            _annotation_label(_component(
                "node", "record", (_label_annotation("node", "First;Second"),),
            ))

    def test_shared_label_reading_still_applies_to_the_neo4j_target(self) -> None:
        self.assertEqual(
            _annotation_label(_component(
                "node", "record", (_label_annotation("node", "Record"),),
            )),
            "Record",
        )
        self.assertEqual(_annotation_label(_component("node", "record")), "record")


if __name__ == "__main__":
    unittest.main()
