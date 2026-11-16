"""Authoring surface type fixture: the single Selection type and inferred types."""
from __future__ import annotations

from typing import assert_type

from kg_build_system import (
    Blueprint,
    Claim,
    Graph,
    GraphOptions,
    Limitation,
    Meaning,
    Omitted,
    Purpose,
    Workflow,
)
from kg_build_system.distribution.languages.asset.model.public import (
    Asset,
    AssetAuthority,
    AssetOptions,
    AssetProfile,
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
    Contract,
    Definition,
    DerivedRowSource,
    Field,
    FieldDefinition,
    DerivedRelation,
    DerivedRelationOptions,
    Stage,
    StageOptions,
    Struct,
    SourceRelation,
    SourceRelationOptions,
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
from kg_build_system.generation import AssetGenerationOptions, asset_generation
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)
from kg_build_system.kernel import Array, Nullable


@asset_generation(AssetGenerationOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(mode="source_relation"),
    package="fixture.tables",
))
class FixtureAsset(Asset):
    options = AssetOptions(
        name="fixture_asset",
        profile=AssetProfile(
            subject="fixture rows",
            coverage="one fixture",
            authority=AssetAuthority.INFERRED,
            basis="typecheck fixture",
        ),
        meaning=Omitted,
    )


class FixtureGraph(Graph):
    options = GraphOptions(
        name="fixture_graph",
        meaning=Meaning(
            purpose=Purpose(
                text="Exercise the authoring surface.",
                limitations=(
                    Limitation(
                        "The fixture does not build graph records.",
                    ),
                ),
            ),
            claims=(Claim("Fixture rows describe sites and regions."),),
        ),
    )


class Address(Struct):
    city: Field[str] = field(name="city", meaning=Omitted)
    postcodes: Field[Array[str]] = field(name="postcodes", meaning=Omitted)


class Detail(Struct):
    label: Field[str] = field(name="label", meaning=Omitted)
    address: Field[Address] = field(name="address", meaning=Omitted)


class Site(SourceRelation[FixtureAsset]):
    options = SourceRelationOptions(
        name="site",
        contract=Contract(
            definition=Definition(
                grain="one row per monitored site", identity=("id",),
            ),
            meaning=Meaning(
                claims=(Claim("One row is one monitored site."),),
            ),
        ),
    )
    site_id: Field[str] = field(
        name="id",
        definition=FieldDefinition(
            value="The site's stable identifier.",
            null_meaning="The source holds no identifier for the site.",
        ),
        meaning=Omitted,
    )
    region_id: Field[str] = field(name="region_id", meaning=Omitted)
    count: Field[int] = field(name="count", meaning=Omitted)
    detail: Field[Detail] = field(name="detail", meaning=Omitted)
    addresses: Field[Array[Address]] = field(name="addresses", meaning=Omitted)
    tags: Field[Array[str]] = field(name="tags", meaning=Omitted)
    labels: Field[Array[Nullable[str]]] = field(name="labels", meaning=Omitted)


class Region(SourceRelation[FixtureAsset]):
    options = SourceRelationOptions(name="region", contract=Omitted)
    region_id: Field[str] = field(name="region_id", meaning=Omitted)
    name: Field[str] = field(name="name", meaning=Omitted)


class Summary(ComputedStruct):
    total = computed_field(Site.count.alter_rows().drop_null(), meaning=Omitted)
    address = computed_field(
        Site.detail.extract(lambda value: value.address), 
        meaning=Omitted,
    )


class SiteStage(Stage(Site.row_source())):
    options = StageOptions(
        definition=Definition(
            grain="one row per monitored site", identity=("site_id",),
        ),
    )
    site_id = computed_field(Site.site_id.alter_rows().drop_null(), meaning=Omitted)


class SiteDerivedRelation(DerivedRelation(SiteStage.row_source())):
    options = DerivedRelationOptions(
        contract=Contract(
            definition=Definition(
                grain="one row per monitored site", identity=("site_id",),
            ),
            meaning=Meaning(
                purpose=Purpose("Read one monitored site."),
                claims=(Claim("One row is one monitored site."),),
            ),
        ),
    )
    site_id = computed_field(SiteStage.site_id, meaning=Omitted)
    summary = computed_field(Site.detail, meaning=Omitted)
    parent_name = computed_field(Site.site_id, meaning=Omitted)


class SiteNode(Node):
    options = NodeOptions(name="site_node", meaning=Omitted)
    label: PropertySlot[str] = property(
        meaning=Meaning(
            purpose=Purpose(
                text="Use the label as the site display name.",
                limitations=(
                    Limitation("Labels are not unique across sites."),
                ),
            ),
        ),
    )


assert_type(Site.site_id, Selection[Nullable[str]])
assert_type(Site.site_id, NullableSelection[str])
assert_type(Site.detail, Selection[Nullable[Detail]])
assert_type(Site.tags, Selection[Nullable[Array[str]]])
assert_type(SiteDerivedRelation.site_id, Selection[str])
assert_type(SiteDerivedRelation.summary, Selection[Nullable[Detail]])
assert_type(SiteDerivedRelation.parent_name, Selection[Nullable[str]])
assert_type(Summary.total, Selection[int])
assert_type(Summary.address, Selection[Nullable[Address]])
assert_type(value_expression("x"), Selection[str])

# A present value satisfies a nullable slot: `Nullable[T]` is `T | None`.
_present_to_nullable: Selection[Nullable[str]] = value_expression("x")

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


binding = node_binding(
    target=SiteNode,
    rows=Site.row_source(),
    bind=bind,
    meaning=Meaning(
        purpose=Purpose("Fulfil the site record from the site relation."),
        claims=(Claim("One site row yields one site node."),),
    ),
)
assert_type(binding, NodeBinding[SiteNode])


# A manifest states composition values; building is a separate step.
manifest_blueprint = Blueprint(namespace_path=".")
manifest_workflow = Workflow(blueprint=manifest_blueprint)
assert_type(manifest_blueprint, Blueprint)
assert_type(manifest_workflow, Workflow)


# ---------------------------------------------------------------------------
# Typing precision: the public surface names the model, not Any.
# ---------------------------------------------------------------------------
from collections.abc import Sequence
from datetime import date

from kg_build_system import (
    DEFAULT_TOOLCHAIN,
    GraphBlueprint,
    NullableComputedField,
    compile,
    default_toolchain,
    edge_binding,
    endpoint,
)
from kg_build_system.distribution.languages.binding.model.public import (
    EdgeBinding,
    EdgeValues,
)
from kg_build_system.distribution.languages.data.model.public import (
    RelationRowSource,
    StageRowSource,
)
from kg_build_system.distribution.languages.topology.model.public import (
    Edge,
    EdgeRoot,
    Endpoint,
)
from kg_build_system.kernel import (
    Key,
    Language,
    NullableType,
    Planner,
    ResourceRegistry,
    ResourceView,
    STR,
    Symbol,
    Toolchain,
    WorkflowPlan,
)


class SiteEdge(Edge[SiteNode, SiteNode]):
    weight: PropertySlot[int] = property(meaning=Omitted)


def bind_edge(row: Site) -> EdgeValues[SiteEdge, str, str, str]:
    return EdgeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.region_id.alter_rows().drop_null(),
        properties=SiteEdge(weight=row.count.alter_rows().drop_null()),
    )


assert_type(
    computed_field(Site.count.alter_rows().drop_null(), meaning=Omitted),
    Field[int],
)
assert_type(
    computed_field(Site.detail, meaning=Omitted),
    NullableComputedField[Detail],
)
assert_type(value_expression(date(2024, 1, 1)), Selection[date])
assert_type(value_expression(["a"]), Selection[Array[str]])
assert_type(
    value_expression(None, logical_type=NullableType(STR)),
    Selection[None],
)
_null_str: Selection[Nullable[str]] = value_expression(
    None, logical_type=NullableType(STR),
)
assert_type(Site.row_source(), RelationRowSource[Site])
assert_type(SiteStage.row_source(), StageRowSource[SiteStage])
assert_type(Node.options, NodeOptions)
_edge_root: type[EdgeRoot] = SiteEdge
assert_type(endpoint(SiteNode), Endpoint[SiteNode])
assert_type(DEFAULT_TOOLCHAIN, Toolchain[GraphBlueprint])
assert_type(default_toolchain(), Toolchain[GraphBlueprint])
assert_type(compile(planners=()), WorkflowPlan)
assert_type(ResourceRegistry().get(str), str)
assert_type(ResourceView({str: "available"}).get(str), str)
assert_type(Symbol(Key(("site",)), "node", "value").value, object)
assert_type(manifest_blueprint.languages, Sequence[Language] | None)
assert_type(manifest_workflow.planners, Sequence[Planner[GraphBlueprint]])
assert_type(manifest_workflow.toolchain, Toolchain[GraphBlueprint] | None)
assert_type(
    edge_binding(
        target=SiteEdge,
        rows=Site.row_source(),
        bind=bind_edge,
        meaning=Meaning(
            purpose=Purpose("Fulfil the site edge from the site relation."),
        ),
    ),
    EdgeBinding[SiteEdge],
)
