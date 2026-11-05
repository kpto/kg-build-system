"""Authoring surface type fixture: the single Selection type and inferred types."""
from __future__ import annotations

from typing import assert_type

from kg_build_system.distribution.languages.asset.model.public import (
    Asset,
    AssetAuthority,
    AssetOptions,
    AssetSemantics,
)
from kg_build_system.distribution.languages.expressions.model.public import (
    NullableSelection,
    Pair,
    Selection,
)
from kg_build_system.distribution.languages.expressions.service.public import (
    value_expression,
)
from kg_build_system.distribution.languages.binding.model.public import (
    NodeBinding,
    NodeValues,
)
from kg_build_system.distribution.languages.binding.service.public import (
    node_binding,
)
from kg_build_system.distribution.languages.data.model.public import (
    ComputedStruct,
    DerivedRowSource,
    Field,
    Projection,
    Struct,
    Table,
    TableOptions,
)
from kg_build_system.distribution.languages.data.service.public import (
    computed_field,
    field,
)
from kg_build_system.distribution.languages.topology.model.public import (
    Node,
    NodeOptions,
    PropertySlot,
)
from kg_build_system.distribution.languages.topology.service.public import (
    property,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)
from kg_build_system.kernel import Array, Nullable


@asset_contract(AssetContractOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(mode="table"),
    package="fixture.tables",
))
class FixtureAsset(Asset):
    options = AssetOptions(
        name="fixture_asset",
        semantics=AssetSemantics(
            subject="fixture rows",
            coverage="one fixture",
            authority=AssetAuthority.INFERRED,
            basis="typecheck fixture",
        ),
    )


class Address(Struct):
    city: Field[str] = field(name="city")
    postcodes: Field[Array[str]] = field(name="postcodes")


class Detail(Struct):
    label: Field[str] = field(name="label")
    address: Field[Address] = field(name="address")


class Site(Table[FixtureAsset]):
    options = TableOptions(name="site")
    site_id: Field[str] = field(name="id")
    region_id: Field[str] = field(name="region_id")
    count: Field[int] = field(name="count")
    detail: Field[Detail] = field(name="detail")
    addresses: Field[Array[Address]] = field(name="addresses")
    tags: Field[Array[str]] = field(name="tags")
    labels: Field[Array[Nullable[str]]] = field(name="labels")


class Region(Table[FixtureAsset]):
    options = TableOptions(name="region")
    region_id: Field[str] = field(name="region_id")
    name: Field[str] = field(name="name")


class Summary(ComputedStruct):
    total = computed_field(Site.count.alter_rows().drop_null())
    address = computed_field(
        Site.detail.extract(lambda value: value.address)
    )


class SiteProjection(Projection(Site.row_source())):
    site_id = computed_field(Site.site_id.alter_rows().drop_null())
    summary = computed_field(Site.detail)
    parent_name = computed_field(Site.site_id)


class SiteNode(Node):
    options = NodeOptions(name="site_node")
    label: PropertySlot[str] = property()


assert_type(Site.site_id, Selection[Nullable[str]])
assert_type(Site.site_id, NullableSelection[str])
assert_type(Site.detail, Selection[Nullable[Detail]])
assert_type(Site.tags, Selection[Nullable[Array[str]]])
assert_type(SiteProjection.site_id, Selection[str])
assert_type(SiteProjection.summary, Selection[Nullable[Detail]])
assert_type(SiteProjection.parent_name, Selection[Nullable[str]])
assert_type(Summary.total, Selection[int])
assert_type(Summary.address, Selection[Nullable[Address]])
assert_type(value_expression("x"), Selection[str])

assert_type(Site.site_id.alter_rows().drop_null(), Selection[str])
assert_type(Site.tags.alter_rows().expand(), Selection[str])
assert_type(Site.addresses.alter_rows().drop_null().alter_rows().expand(), Selection[Address])
assert_type(Site.detail.extract(lambda value: value.label), Selection[Nullable[str]])
assert_type(Summary.address.extract(lambda value: value.city), Selection[Nullable[str]])
assert_type(Site.tags.alter_rows().drop_null().at(0), Selection[Nullable[str]])
assert_type(Site.tags.alter_rows().drop_null().unique(), Selection[Array[str]])
assert_type(Site.tags.alter_rows().drop_null().sort(), Selection[Array[str]])
assert_type(Site.tags.alter_rows().drop_null().concat(","), Selection[str])
assert_type(
    Site.tags.alter_rows().drop_null().transform_items(
        lambda item: item.prepend("kg:")
    ),
    Selection[Array[str]],
)
assert_type(
    Site.labels.alter_rows().drop_null().drop_null_items(),
    Selection[Array[str]],
)
assert_type(
    Site.region_id.lookup(Region, Site.region_id),
    Selection[Nullable[Array[Region]]],
)
assert_type(
    Site.tags.alter_rows().drop_null().zip(
        Site.tags.alter_rows().drop_null()
    ),
    Selection[Array[Pair[str, str]]],
)
assert_type(
    Site.tags.alter_rows().drop_null().zip(
        Site.tags.alter_rows().drop_null()
    ).alter_rows().expand().extract(lambda pair: pair.left),
    Selection[str],
)
assert_type(
    Site.row_source().unnest(lambda site: site.tags),
    DerivedRowSource[Site],
)


def bind(row: Site) -> NodeValues[SiteNode, str]:
    return NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(label=row.site_id.alter_rows().drop_null()),
    )


binding = node_binding(target=SiteNode, rows=Site.row_source(), bind=bind)
assert_type(binding, NodeBinding[SiteNode])
