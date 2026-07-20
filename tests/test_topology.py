"""Tests for the topology model."""

import unittest

from demo.topology import TOPOLOGY
from kg_build_system.topology import (
    Edge,
    EdgeType,
    IdentifierRef,
    Neo4jIndex,
    Node,
    NodeType,
    Ontology,
    PropertyRef,
    Topology,
    TopologyValidationError,
    edge,
    node,
    topology,
)


class TopologyTests(unittest.TestCase):
    def test_round_trip_json(self) -> None:
        topology = Topology(
            name="Example",
            nodes=(NodeType(name="Thing"),),
            edges=(),
        )

        self.assertEqual(Topology.from_json(topology.to_json()), topology)

    def test_edge_requires_declared_endpoints(self) -> None:
        with self.assertRaises(TopologyValidationError):
            Topology(
                name="Example",
                nodes=(NodeType(name="Thing"),),
                edges=(EdgeType(name="RelatesTo", source="Thing", target="Missing"),),
            )

    def test_declarations_expose_typed_property_references(self) -> None:
        class NamedEntity(Node):
            name: PropertyRef[str] = PropertyRef[str](nullable=False)

        @node(description="Target node")
        class Target(NamedEntity):
            id: IdentifierRef[str] = IdentifierRef[str]()
            symbol: PropertyRef[str] = PropertyRef[str](
                nullable=False,
                annotations=[Neo4jIndex()],
            )

        class Disease(NamedEntity):
            id: IdentifierRef[str] = IdentifierRef[str]()

        class ScoredRelationship(Edge[Target, Disease]):
            score: PropertyRef[float] = PropertyRef[float](nullable=False)

        @edge(description="Associated edge")
        class AssociatedWith(ScoredRelationship):
            pass

        graph = topology("Example", nodes=(Target, Disease), edges=(AssociatedWith,))

        self.assertIsInstance(Target.symbol, PropertyRef)
        self.assertEqual(Target.symbol.python_type, str)
        self.assertEqual(Target.symbol.annotations[0], Neo4jIndex())
        self.assertEqual(AssociatedWith.score.python_type, float)
        self.assertEqual(graph.nodes[0].description, "Target node")
        self.assertEqual(graph.edges[0].description, "Associated edge")
        self.assertEqual([property_.name for property_ in graph.nodes[0].properties], ["name", "symbol"])
        self.assertEqual(graph.edges[0].properties[0].name, "score")

    def test_python_demo_serializes_and_round_trips(self) -> None:
        serialized_topology = TOPOLOGY.to_json()
        deserialized_topology = Topology.from_json(serialized_topology)

        self.assertEqual(TOPOLOGY, deserialized_topology)

    def test_ontology_is_a_reusable_partial_annotation(self) -> None:
        so = Ontology("http://purl.obolibrary.org/obo/so.owl", id="so")

        annotation = so("0000704")

        self.assertEqual(annotation.term, "0000704")
        self.assertEqual(annotation.ontology, so)
