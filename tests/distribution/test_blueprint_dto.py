from __future__ import annotations

import unittest
from dataclasses import fields
from typing import get_args, get_origin, get_type_hints

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.asset.model.internal import (
    AssetDTO,
    AssetPartDTO,
    AssetSemanticsDTO,
)
from kg_build_system.distribution.languages.asset.model.public import AssetAuthority
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
    StructDTO,
)
from kg_build_system.distribution.languages.topology.model.internal import (
    EdgeDTO,
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
)
from kg_build_system.distribution.model.public.refs import (
    AssetRef, NodeRef, PropertyRef, RelationRef,
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
    StructDTO,
    AssetDTO,
    AssetPartDTO,
    EdgeDTO,
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
    EdgeBindingDTO,
    NodeBindingDTO,
    PythonRefDTO,
)


def _asset() -> AssetPartDTO:
    return AssetPartDTO(assets=(
        AssetDTO(
            "estate",
            AssetSemanticsDTO(
                subject="estate records",
                coverage="sites",
                authority=AssetAuthority.PRIMARY,
                basis="test fixture",
            ),
        ),
    ))


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
    relation = RelationDTO(
        name="site",
        columns=(),
        asset=AssetRef("asset", Key(("estate",))),
    )
    data = DataPartDTO(
        structs=(),
        relations=(relation,),
        projections=(),
    )
    assets = _asset()
    return GraphBlueprint(
        graph=GraphPartDTO(nodes=(documented, site, unit, monitored), edges=(edge,)),
        data=data,
        assets=assets,
        bindings=(),
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

    def test_a_relation_names_its_asset(self) -> None:
        relation = _blueprint().data.relations[0]

        self.assertIsInstance(relation.asset, AssetRef)
        self.assertEqual(
            relation.asset.to_document(), ["asset", "asset", "estate"],
        )

    def test_the_data_part_has_structs_relations_and_projections_only(self) -> None:
        self.assertEqual(
            {field.name for field in fields(DataPartDTO)},
            {"structs", "relations", "projections"},
        )

    def test_the_public_blueprint_references_layer_dtos(self) -> None:
        hints = get_type_hints(GraphBlueprint)

        self.assertIs(hints["graph"], GraphPartDTO)
        self.assertIs(hints["data"], DataPartDTO)
        self.assertIs(hints["assets"], AssetPartDTO)
        self.assertEqual(get_origin(hints["bindings"]), tuple)
        self.assertEqual(get_args(hints["bindings"])[0], BindingDTO)
        self.assertNotIn("sources", hints)

    def test_an_empty_blueprint_has_the_layer_shapes(self) -> None:
        blueprint = _blueprint()

        self.assertIsInstance(blueprint.graph, GraphPartDTO)
        self.assertIsInstance(blueprint.data, DataPartDTO)
        self.assertIsInstance(blueprint.assets, AssetPartDTO)


if __name__ == "__main__":
    unittest.main()
