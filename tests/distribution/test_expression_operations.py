"""Contract tests for lookup, zip and row-source unnest."""
from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path

import duckdb

from kg_build_system import (
    Array,
    Field,
    Nullable,
    Table,
    computed_field,
    create_blueprint,
    field,
)
from kg_build_system.distribution.interpreter.service.internal import (
    blueprint_to_document,
    blueprint_to_source,
)
from kg_build_system.distribution.languages.data import Projection
from kg_build_system.distribution.languages.data.model.internal import (
    DataPartDTO,
    ProjectionDTO,
    RowScanDTO,
    RowUnnestDTO,
)
from kg_build_system.distribution.languages.data.model.public import (
    ShapeField,
)
from kg_build_system.distribution.languages.data.service.internal import (
    data_from_document,
    data_to_document,
    row_source_key,
    row_source_plan_dto,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
    LookupExpressionDTO,
    OperationExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    as_expression,
    expression_dto,
    expression_from_document,
    expression_to_document,
)
from kg_build_system.distribution.modules.duckdb.service._private.emitters import (
    DEFAULT_EMITTER,
)
from kg_build_system.distribution.service.internal.emission import (
    RelationPlan,
    Scan,
)
from kg_build_system.kernel import ArrayType, NullableType, StructType
from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO
from tests.distribution.support import TestEstate


class Region(Table[TestEstate]):
    region_id: Field[str] = field(name="region_id")
    name: Field[str] = field(name="name")


class Site(Table[TestEstate]):
    site_id: Field[str] = field(name="site_id")
    region_id: Field[str] = field(name="region_id")
    tags: Field[Array[str]] = field(name="tags")
    labels: Field[Array[str]] = field(name="labels")


class RegionProjection(Projection(Region.row_source())):
    region_id = computed_field(Region.region_id.alter_rows().drop_null())
    name = computed_field(Region.name.alter_rows().drop_null())


def _dto(selection: object) -> ExpressionDTO:
    return expression_dto(as_expression(selection).model)


class LookupTests(unittest.TestCase):
    def test_lookup_returns_a_nullable_array_of_the_target_shape(self) -> None:
        lookup = Site.region_id.lookup(Region, Site.region_id)

        self.assertIsInstance(lookup.logical_type, NullableType)
        array = lookup.logical_type.value
        self.assertIsInstance(array, ArrayType)
        self.assertIsInstance(array.item, StructType)
        self.assertEqual(array.item.qualname, Region.__qualname__)

    def test_lookup_composes_left_inner_and_one_row_per_match(self) -> None:
        lookup = Site.region_id.lookup(Region, Site.region_id)

        left = lookup
        self.assertIsInstance(left.logical_type, NullableType)

        inner = lookup.alter_rows().drop_null()
        self.assertIsInstance(inner.logical_type, ArrayType)

        one_per_match = inner.alter_rows().expand()
        self.assertIsInstance(one_per_match.logical_type, StructType)
        name = one_per_match.extract(lambda region: region.name)
        self.assertIsInstance(name.logical_type, NullableType)

    def test_lookup_takes_no_how_and_uses_a_typed_relation_reference(self) -> None:
        with self.assertRaises(TypeError):
            Site.region_id.lookup(
                Region, Site.region_id, how="left",  # type: ignore[call-arg]
            )

        document = expression_to_document(
            _dto(Site.region_id.lookup(Region, Site.region_id)),
        )
        self.assertEqual(document["kind"], "lookup")
        self.assertEqual(document["relation"], ["data", "relation", "region"])
        self.assertEqual(document["target_field"], "region_id")
        self.assertEqual(
            expression_from_document(document),
            _dto(Site.region_id.lookup(Region, Site.region_id)),
        )
        self.assertIsInstance(_dto(
            Site.region_id.lookup(Region, Site.region_id)
        ), LookupExpressionDTO)

    def test_lookup_can_target_a_projection(self) -> None:
        lookup = Site.region_id.lookup(
            RegionProjection, Site.region_id, target_key="region_id",
        )
        self.assertIsInstance(lookup.logical_type, NullableType)
        self.assertEqual(
            lookup.logical_type.value.item.qualname,
            RegionProjection.shape.__qualname__,
        )

    def test_lookup_executes_as_a_keyed_array_of_records(self) -> None:
        lookup = Site.region_id.lookup(Region, Site.region_id)
        relation_plan = RelationPlan(
            (Scan("site", "sites", "t0"),),
            (),
            (),
            (("hits", _dto(lookup)),),
            relations={"region": "regions"},
            shapes={
                "region": (
                    ShapeField("region_id", "region_id", UnitTypeDTO("str")),
                    ShapeField("name", "name", UnitTypeDTO("str")),
                ),
            },
        )
        sql = DEFAULT_EMITTER.relation_sql(relation_plan)
        connection = duckdb.connect()
        try:
            connection.execute("CREATE TABLE sites(region_id VARCHAR)")
            connection.execute(
                "INSERT INTO sites VALUES ('r1'), ('r1'), ('r9'), (NULL)"
            )
            connection.execute(
                "CREATE TABLE regions(region_id VARCHAR, name VARCHAR)"
            )
            connection.execute(
                "INSERT INTO regions VALUES ('r1', 'North'), ('r2', 'South')"
            )
            rows = connection.execute(sql).fetchall()
        finally:
            connection.close()

        self.assertEqual(
            rows,
            [
                ([{"region_id": "r1", "name": "North"}],),
                ([{"region_id": "r1", "name": "North"}],),
                (None,),
                (None,),
            ],
        )


class ZipTests(unittest.TestCase):
    def test_zip_pairs_two_arrays_at_value_level(self) -> None:
        paired = (
            Site.tags.alter_rows().drop_null()
            .zip(Site.labels.alter_rows().drop_null())
        )
        self.assertIsInstance(paired.logical_type, ArrayType)
        pair = paired.logical_type.item
        self.assertIsInstance(pair, StructType)
        self.assertIn("Pair_", pair.qualname)

        expanded = paired.alter_rows().expand()
        self.assertEqual(
            expanded.extract(lambda value: value.left).logical_type.name, "str",
        )
        self.assertEqual(
            expanded.extract(lambda value: value.right).logical_type.name, "str",
        )

    def test_zip_dto_carries_both_array_inputs(self) -> None:
        paired = (
            Site.tags.alter_rows().drop_null()
            .zip(Site.labels.alter_rows().drop_null())
        )
        dto = _dto(paired)
        self.assertIsInstance(dto, OperationExpressionDTO)
        self.assertEqual(dto.operator.name, "zip")
        self.assertEqual(len(dto.arguments), 2)
        self.assertEqual(
            expression_from_document(expression_to_document(dto)), dto,
        )

    def test_zip_executes_by_position_and_refuses_a_length_mismatch(self) -> None:
        paired = (
            Site.tags.alter_rows().drop_null()
            .zip(Site.labels.alter_rows().drop_null())
        )
        expression = DEFAULT_EMITTER.expression_sql(
            _dto(paired), aliases={"site": "t0"},
        )
        connection = duckdb.connect()
        try:
            connection.execute(
                "CREATE TABLE sites(tags VARCHAR[], labels VARCHAR[])"
            )
            connection.execute(
                "INSERT INTO sites VALUES "
                "(['a', 'b'], ['x', 'y']), ([], [])"
            )
            rows = connection.execute(
                f"SELECT {expression} FROM sites AS t0"
            ).fetchall()
            self.assertEqual(
                rows,
                [
                    ([{"left": "a", "right": "x"}, {"left": "b", "right": "y"}],),
                    ([],),
                ],
            )
            connection.execute("INSERT INTO sites VALUES (['a'], ['x', 'y'])")
            with self.assertRaisesRegex(Exception, "equal length"):
                connection.execute(f"SELECT {expression} FROM sites AS t0")
        finally:
            connection.close()


class UnnestTests(unittest.TestCase):
    def test_unnest_narrows_the_selected_field_to_its_item_shape(self) -> None:
        source = Site.row_source().unnest(lambda site: site.tags)

        fields = {
            item.name: item.logical_type
            for item in source.shape._kg_row_source_fields
        }
        self.assertEqual(fields["tags"].name, "str")
        self.assertIn("site_id", fields)

    def test_unnest_plan_round_trips_and_carries_its_expression(self) -> None:
        source = Site.row_source().unnest(lambda site: site.tags)
        plan = row_source_plan_dto(source)
        self.assertIsInstance(plan, RowUnnestDTO)
        self.assertEqual(plan.field, "tags")
        self.assertEqual(plan.expression.field.field, "tags")

        part = DataPartDTO((), (), (
            ProjectionDTO("tags", (), plan),
        ))
        restored = data_from_document(data_to_document(part))
        self.assertEqual(restored.projections[0].row_source, plan)

    def test_unnest_executes_one_row_per_item_and_none_for_empty(self) -> None:
        source = Site.row_source().unnest(lambda site: site.tags)
        plan = row_source_plan_dto(source)
        self.assertIsInstance(plan, RowUnnestDTO)
        assert isinstance(plan, RowUnnestDTO)
        assert isinstance(plan.input, RowScanDTO)
        sql = DEFAULT_EMITTER.emit_row_source(
            plan,
            {row_source_key(plan.input): "sites"},
            {},
        )
        connection = duckdb.connect()
        try:
            connection.execute(
                "CREATE TABLE sites(site_id VARCHAR, tags VARCHAR[])"
            )
            connection.execute(
                "INSERT INTO sites VALUES "
                "('a', ['x', 'y']), ('b', []), ('c', NULL)"
            )
            rows = connection.execute(sql).fetchall()
        finally:
            connection.close()

        self.assertEqual(
            [(row[0], row[1]) for row in rows],
            [("a", "x"), ("a", "y")],
        )


class BlueprintSourceRoundTripTests(unittest.TestCase):
    def test_lookup_zip_and_unnest_survive_source_round_trip(self) -> None:
        source = '''
from kg_build_system import (
    Array, Asset, AssetAuthority, AssetOptions, AssetSemantics, Field,
    Projection, ProjectionOptions, Table, TableOptions, computed_field, field,
)

class Estate(Asset):
    options = AssetOptions(
        name="estate",
        semantics=AssetSemantics(
            subject="x", coverage="y",
            authority=AssetAuthority.PRIMARY, basis="z",
        ),
    )

class Region(Table[Estate]):
    options = TableOptions(name="region")
    region_id: Field[str] = field(name="region_id")
    name: Field[str] = field(name="name")

class Site(Table[Estate]):
    options = TableOptions(name="site")
    site_id: Field[str] = field(name="site_id")
    region_id: Field[str] = field(name="region_id")
    tags: Field[Array[str]] = field(name="tags")
    labels: Field[Array[str]] = field(name="labels")

class Tagged(Projection(Site.row_source().unnest(lambda row: row.tags))):
    options = ProjectionOptions(name="tagged")
    site_id = computed_field(Site.site_id.alter_rows().drop_null())

class Joined(Projection(Site.row_source())):
    options = ProjectionOptions(name="joined")
    site_id = computed_field(Site.site_id.alter_rows().drop_null())
    region_name = computed_field(
        Site.region_id.lookup(Region, Site.region_id)
        .alter_rows().drop_null().alter_rows().expand()
        .extract(lambda region: region.name)
    )
    pairs = computed_field(
        Site.tags.alter_rows().drop_null()
        .zip(Site.labels.alter_rows().drop_null())
    )
'''

        def recreate(text: str):
            with tempfile.TemporaryDirectory() as directory:
                package = Path(directory) / f"graph_{uuid.uuid4().hex}"
                package.mkdir()
                (package / "__init__.py").write_text("")
                (package / "graph.py").write_text(text)
                return create_blueprint(namespace_path=package)

        first = recreate(source)
        second = recreate(blueprint_to_source(first, None))
        self.assertEqual(
            json.dumps(blueprint_to_document(first), sort_keys=True),
            json.dumps(blueprint_to_document(second), sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
