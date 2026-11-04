from __future__ import annotations

import unittest
from dataclasses import fields
from typing import get_args, get_origin, get_type_hints

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal import (
    BindingDTO,
    EdgeBindingDTO,
    NodeBindingDTO,
    PythonRefDTO,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ColumnDTO,
    DataPartDTO,
    ProjectionDTO,
    RelationDTO,
    RowDistinctDTO,
    RowFilterDTO,
    RowGroupByDTO,
    RowJoinDTO,
    RowOrderByDTO,
    RowScanDTO,
    RowUnionDTO,
    SourceDTO,
    StructDTO,
)
from kg_build_system.distribution.languages.topology.model.internal import (
    EdgeDTO,
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
)
from kg_build_system.distribution.model.public.refs import (
    NodeRef, PropertyRef, RelationRef,
)
from kg_build_system.kernel import Key
from kg_build_system.kernel.model.internal import UnitTypeDTO


DTO_TYPES = (
    ColumnDTO,
    DataPartDTO,
    ProjectionDTO,
    RelationDTO,
    RowDistinctDTO,
    RowFilterDTO,
    RowGroupByDTO,
    RowJoinDTO,
    RowOrderByDTO,
    RowScanDTO,
    RowUnionDTO,
    SourceDTO,
    StructDTO,
    EdgeDTO,
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
    EdgeBindingDTO,
    NodeBindingDTO,
    PythonRefDTO,
)


def _blueprint() -> GraphBlueprint:
    documented = NodeDTO(name="documented", abstract=True)
    site = NodeDTO(
        name="site",
        labels=("Site",),
        properties=(
            PropertyDTO(
                "name",
                UnitTypeDTO("str"),
                PropertyRef("topology", Key(("site.name",))),
            ),
        ),
        parent=NodeRef("topology", Key(("documented",))),
    )
    unit = NodeDTO(name="unit", labels=("Unit",))
    monitored = NodeDTO(name="monitored", abstract=True)
    edge = EdgeDTO(
        name="has_unit",
        labels=("HAS_UNIT",),
        source=NodeRef("topology", Key(("site",))),
        target=NodeRef("topology", Key(("unit",))),
        parent=NodeRef("topology", Key(("monitored",))),
    )
    source = SourceDTO(
        relation=RelationRef("data", Key(("site",))),
        location="sites.csv",
        format="csv",
    )
    data = DataPartDTO(
        structs=(),
        relations=(),
        projections=(),
        sources=(source,),
    )
    return GraphBlueprint(
        graph=GraphPartDTO(nodes=(documented, site, unit, monitored), edges=(edge,)),
        data=data,
        bindings=(),
        sources=data.sources,
    )


class BlueprintDTOTests(unittest.TestCase):
    def test_no_layer_dto_carries_a_symbol_id(self) -> None:
        for dto_type in DTO_TYPES:
            with self.subTest(dto_type=dto_type.__name__):
                self.assertNotIn(
                    "symbol_id",
                    {field.name for field in fields(dto_type)},
                )

    def test_topology_endpoints_and_parents_are_node_refs(self) -> None:
        blueprint = _blueprint()
        names = {node.name for node in blueprint.graph.nodes}

        for edge in blueprint.graph.edges:
            with self.subTest(edge=edge.name):
                self.assertIsInstance(edge.source, NodeRef)
                self.assertIsInstance(edge.target, NodeRef)
                self.assertIn(edge.source.name, names)
                self.assertIn(edge.target.name, names)

        for node in blueprint.graph.nodes:
            with self.subTest(node=node.name):
                if node.parent is not None:
                    self.assertIsInstance(node.parent, NodeRef)
                    self.assertIn(node.parent.name, names)

    def test_the_public_blueprint_references_layer_dtos(self) -> None:
        hints = get_type_hints(GraphBlueprint)

        self.assertIs(hints["graph"], GraphPartDTO)
        self.assertIs(hints["data"], DataPartDTO)
        self.assertEqual(get_origin(hints["bindings"]), tuple)
        self.assertEqual(get_args(hints["bindings"])[0], BindingDTO)
        self.assertEqual(get_origin(hints["sources"]), tuple)
        self.assertEqual(get_args(hints["sources"])[0], SourceDTO)

    def test_an_empty_blueprint_has_the_layer_shapes(self) -> None:
        blueprint = _blueprint()

        self.assertIsInstance(blueprint.graph, GraphPartDTO)
        self.assertIsInstance(blueprint.data, DataPartDTO)
        self.assertIsInstance(blueprint.sources[0], SourceDTO)


if __name__ == "__main__":
    unittest.main()
