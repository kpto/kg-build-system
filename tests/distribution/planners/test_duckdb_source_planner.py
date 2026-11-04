"""Contract tests for the shared asset-table query and DuckDB source planner."""
from __future__ import annotations

import unittest

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.asset.model.internal import (
    AssetDTO,
    AssetLayoutDTO,
    AssetPartDTO,
    AssetSemanticsDTO,
)
from kg_build_system.distribution.languages.asset.model.public import AssetAuthority
from kg_build_system.distribution.languages.binding.model.internal import (
    NodeBindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ColumnDTO,
    DataPartDTO,
    RelationDTO,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    FieldReferenceDTO,
)
from kg_build_system.distribution.languages.topology.model.internal import (
    GraphPartDTO,
    NodeDTO,
)
from kg_build_system.distribution.model.public.refs import (
    AssetRef, FieldRef, NodeRef,
)
from kg_build_system.distribution.modules.duckdb import DuckDbSourcePlanner
from kg_build_system.distribution.service.public import asset_tables, table_relations
from kg_build_system.kernel import Key, PlanContext
from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO


def _asset(layout: AssetLayoutDTO | None) -> AssetPartDTO:
    return AssetPartDTO(assets=(
        AssetDTO(
            "estate",
            AssetSemanticsDTO(
                subject="estate",
                coverage="sites",
                authority=AssetAuthority.PRIMARY,
                basis="test fixture",
            ),
            layout=layout,
        ),
    ))


def _relation(name: str) -> RelationDTO:
    return RelationDTO(
        name,
        (
            ColumnDTO(
                "site_id",
                UnitTypeDTO("str"),
                FieldRef("data", Key((f"{name}.site_id",))),
            ),
        ),
        AssetRef("asset", Key(("estate",))),
    )


def _read(relation: str) -> FieldReferenceDTO:
    return FieldReferenceDTO(
        logical_type=UnitTypeDTO("str"),
        field=FieldRef("data", Key((f"{relation}.site_id",))),
        path=(),
    )


def _blueprint(
    layout: AssetLayoutDTO | None,
    *,
    relations: tuple[str, ...] = ("sites",),
    read: str = "sites",
) -> GraphBlueprint:
    node = NodeDTO("site", labels=("Site",))
    binding = NodeBindingDTO(
        NodeRef("topology", Key(("site",))), _read(read),
    )
    return GraphBlueprint(
        graph=GraphPartDTO(nodes=(node,)),
        data=DataPartDTO(
            structs=(),
            relations=tuple(_relation(name) for name in relations),
            projections=(),
        ),
        assets=_asset(layout),
        bindings=(binding,),
    )


def _step(blueprint: GraphBlueprint):
    (step,) = DuckDbSourcePlanner().plan(blueprint, PlanContext())
    return step


class AssetTableTests(unittest.TestCase):
    def test_only_read_tables_are_included_and_sorted(self) -> None:
        blueprint = _blueprint(
            None, relations=("zebra", "sites"), read="sites",
        )

        tables = asset_tables(blueprint)

        self.assertEqual([table.relation_name for table in tables], ["sites"])
        self.assertEqual(table_relations(blueprint), {"sites": "kg_table_0"})

    def test_tables_are_numbered_in_relation_order(self) -> None:
        blueprint = _blueprint(
            None, relations=("zebra", "sites"), read="sites",
        )
        second = RelationDTO(
            "zebra",
            _relation("zebra").columns,
            AssetRef("asset", Key(("estate",))),
        )
        bindings = (
            NodeBindingDTO(NodeRef("topology", Key(("site",))), _read("sites")),
            NodeBindingDTO(NodeRef("topology", Key(("site",))), _read("zebra")),
        )
        blueprint = GraphBlueprint(
            graph=blueprint.graph,
            data=DataPartDTO((), (second, *blueprint.data.relations), ()),
            assets=blueprint.assets,
            bindings=bindings,
        )

        self.assertEqual(
            table_relations(blueprint),
            {"sites": "kg_table_0", "zebra": "kg_table_1"},
        )

    def test_a_blueprint_with_no_relations_has_no_tables(self) -> None:
        blueprint = _blueprint(None)
        blueprint = GraphBlueprint(
            graph=blueprint.graph,
            data=DataPartDTO((), (), ()),
            assets=blueprint.assets,
            bindings=blueprint.bindings,
        )

        self.assertEqual(asset_tables(blueprint), ())


class DuckDbSourcePlannerTests(unittest.TestCase):
    def test_a_member_path_is_joined_to_the_locator(self) -> None:
        layout = AssetLayoutDTO(
            locator="base", format="json",
            members=(("sites", "parts/sites.json"),),
        )

        payload = _step(_blueprint(layout)).instruction.payload

        assert isinstance(payload, dict)
        self.assertEqual(payload["location"], "base/parts/sites.json")

    def test_a_selector_uses_table_and_table_path(self) -> None:
        layout = AssetLayoutDTO(
            locator="base", format="parquet",
            selector="{table_path}/{table}.parquet",
        )

        payload = _step(
            _blueprint(layout, relations=("readings.vibration",), read="readings.vibration"),
        ).instruction.payload

        assert isinstance(payload, dict)
        self.assertEqual(
            payload["location"],
            "base/readings/vibration/readings.vibration.parquet",
        )

    def test_the_locator_is_the_fallback_location(self) -> None:
        layout = AssetLayoutDTO(locator="base/all.json", format="json")

        payload = _step(_blueprint(layout)).instruction.payload

        assert isinstance(payload, dict)
        self.assertEqual(payload["location"], "base/all.json")

    def test_an_absolute_member_is_not_joined(self) -> None:
        layout = AssetLayoutDTO(
            locator="base", format="json",
            members=(("sites", "/mnt/sites.json"),),
        )

        payload = _step(_blueprint(layout)).instruction.payload

        assert isinstance(payload, dict)
        self.assertEqual(payload["location"], "/mnt/sites.json")

    def test_an_unsupported_format_produces_no_step(self) -> None:
        layout = AssetLayoutDTO(locator="base", format="excel")

        self.assertEqual(
            DuckDbSourcePlanner().plan(
                _blueprint(layout), PlanContext(),
            ),
            (),
        )

    def test_the_payload_carries_columns_credentials_and_paths(self) -> None:
        layout = AssetLayoutDTO(
            locator="base", format="json",
            members=(("sites", "sites.json"),),
            properties=(("credentials", "estate-reader"),),
        )

        payload = _step(_blueprint(layout)).instruction.payload

        assert isinstance(payload, dict)
        self.assertEqual(
            set(payload),
            {
                "relation", "location", "format", "credential_reference",
                "declaration", "declared_columns", "declared_paths",
            },
        )
        self.assertEqual(payload["relation"], "kg_table_0")
        self.assertEqual(payload["declaration"], "sites")
        self.assertEqual(payload["credential_reference"], "estate-reader")
        self.assertEqual(
            payload["declared_columns"],
            [{
                "name": "site_id",
                "logical_type": {"kind": "unit", "name": "str"},
            }],
        )


if __name__ == "__main__":
    unittest.main()
