"""A whole realistic project expressed in the IR document.

This is the schema's acceptance test: if the monitored-estate reference project
cannot be written here, the document model is wrong. It is also the generator's
golden input, so the shapes below are what ``generate`` must render.
"""

from __future__ import annotations

import pytest

from studio_backend.ir.document import (
    Annotation,
    AnnotationField,
    AnnotationType,
    ArrayType,
    Binding,
    Component,
    DataField,
    FieldExpression,
    LiteralExpression,
    Module,
    OperationExpression,
    Point,
    Projection,
    ProjectionField,
    Project,
    ProjectDocument,
    Property,
    PropertyBinding,
    Source,
    Struct,
    StructType,
    Table,
    TableGroupMember,
    array,
    nullable,
    unit,
    unwrap_nullable as unwrap,
)
from studio_backend.ir import refs

SITES_PACKAGE = "kg_project.table.sites"


def _field(name: str, value, **changes: object) -> DataField:
    return DataField(name=name, logical_type=value, **changes)  # type: ignore[arg-type]


def _field_ref(source: str, path: tuple[str, ...], value) -> FieldExpression:
    return FieldExpression(source=source, path=path, logical_type=value)


def _non_null(expression: object, value: object, operator: str = "where_present") -> OperationExpression:
    return OperationExpression(  # type: ignore[call-arg]
        operator=operator, arguments=(expression,), logical_type=value  # type: ignore[arg-type]
    )


@pytest.fixture
def document() -> ProjectDocument:
    provenance = AnnotationType(
        id="provenance",
        declaration_name="Provenance",
        namespace="kg_project",
        annotation_id="provenance",
        description="Records which build stage produced or tracks a component.",
        fields=(AnnotationField(name="stage", logical_type=unit("str")),),
    )

    contact_location = Struct(
        id="premises_contact_location",
        declaration_name="PremisesContactLocationStruct",
        name="premises_contact_location",
        fields=(
            _field("city", unit("str", nullable=True)),
            _field("room", unit("str", nullable=True)),
        ),
    )
    contact = contact_location.updated(
        id="premises_contact",
        declaration_name="PremisesContactStruct",
        name="premises_contact",
        fields=(
            _field("email", unit("str", nullable=True)),
            _field(
                "location",
                nullable(StructType(module=SITES_PACKAGE, qualname=contact_location.declaration_name)),
            ),
        ),
    )
    premises = contact_location.updated(
        id="premises",
        declaration_name="PremisesStruct",
        name="premises",
        fields=(
            _field("contact_name", unit("str", nullable=True)),
            _field(
                "contact",
                nullable(StructType(module=SITES_PACKAGE, qualname=contact.declaration_name)),
            ),
        ),
    )

    sites = Table(
        id="sites",
        declaration_name="SitesTable",
        name="sites",
        description="One row per monitored site.",
        fields=(
            _field("site_id", unit("str", nullable=True)),
            _field("site_name", unit("str", nullable=True)),
            _field(
                "premises",
                nullable(StructType(module=SITES_PACKAGE, qualname=premises.declaration_name)),
            ),
            _field("priority_scores", array(unit("int", nullable=True), nullable=True)),
        ),
    )

    equipment = Table(
        id="equipment",
        declaration_name="EquipmentTable",
        name="equipment",
        fields=(
            _field("unit_ref", unit("str", nullable=True)),
            _field("site_id", unit("str", nullable=True)),
            _field("in_service", unit("bool", nullable=True)),
            _field("survey_period", unit("str", nullable=True)),
        ),
    )

    readings = Table(
        id="readings",
        declaration_name="ReadingsTableGroup",
        name="readings",
        members=(
            TableGroupMember(python_name="temperature", ref="temperature_readings"),
            TableGroupMember(python_name="mechanical", ref="mechanical_readings"),
        ),
    )
    mechanical = readings.updated(
        id="mechanical_readings",
        declaration_name="MechanicalTableGroup",
        name="mechanical",
        members=(TableGroupMember(python_name="vibration", ref="vibration_readings"),),
        group="readings",
    )
    temperature = readings.updated(
        id="temperature_readings",
        declaration_name="TemperatureTable",
        name="temperature",
        group="readings",
        fields=(_field("unit_ref", unit("str", nullable=True)), _field("deg_c", unit("float", nullable=True))),
    )
    vibration = readings.updated(
        id="vibration_readings",
        declaration_name="VibrationTable",
        name="vibration",
        group="mechanical_readings",
        fields=(_field("unit_ref", unit("str", nullable=True)), _field("mm_s", unit("float", nullable=True))),
    )

    # A category, a template, and two concrete components using both.
    documented = Component(
        id="documented",
        kind="node",
        tier="category",
        declaration_name="DocumentedAbstractNode",
        name="documented",
        description="Category: every documented entity carries a human-readable summary.",
        label="Documented",
        properties=(_property("summary", unit("str")),),
    )
    provenanced = documented.updated(
        id="provenanced_node",
        tier="template",
        declaration_name="ProvenancedNodeTemplate",
        name="provenanced_node",
        label=None,
        properties=(_property("source_version", unit("str")),),
        annotations=(
            Annotation(import_module="kg_project.annotations", class_name="Provenance", arguments={"stage": "built"}),
        ),
    )
    site = documented.updated(
        id="site",
        tier="concrete",
        declaration_name="SiteNode",
        name="site",
        label="Site",
        parent="documented",
        mixins=("provenanced_node",),
        properties=(_property("name", unit("str")), _property("city", unit("str"))),
    )
    unit_node = site.updated(
        id="unit",
        declaration_name="UnitNode",
        name="unit",
        label="Unit",
        properties=(_property("name", unit("str")), _property("in_service", unit("bool"))),
    )
    monitored = documented.updated(
        id="monitored_relation",
        kind="edge",
        tier="category",
        declaration_name="MonitoredRelationAbstractEdge",
        name="monitored_relation",
        label="MONITORED",
        source="documented",
        target="documented",
        properties=(),
    )
    has_unit = monitored.updated(
        id="has_unit",
        tier="concrete",
        declaration_name="HasUnitEdge",
        name="has_unit",
        label="HAS_UNIT",
        parent="monitored_relation",
        source="site",
        target="unit",
    )

    site_key = unit("str")
    site_binding = Binding(
        id="site_binding",
        kind="node",
        component="site",
        build_key=_non_null(_field_ref("sites", ("site_id",), unit("str", nullable=True)), site_key),
        properties=(
            PropertyBinding(
                name="name",
                expression=OperationExpression(
                    operator="coalesce",
                    arguments=(
                        _field_ref("sites", ("site_name",), unit("str", nullable=True)),
                        LiteralExpression(value="Unnamed site", logical_type=unit("str")),
                    ),
                    logical_type=unit("str"),
                ),
            ),
            PropertyBinding(
                # ``SiteNode.city`` is non-null, and the nested path can be missing at
                # every hop, so the fallback is written down rather than the
                # declaration softened to accept a null.
                name="city",
                expression=OperationExpression(
                    operator="coalesce",
                    arguments=(
                        _field_ref(
                            "sites",
                            ("premises", "contact", "location", "city"),
                            unit("str", nullable=True),
                        ),
                        LiteralExpression(value="Unlisted city", logical_type=unit("str")),
                    ),
                    logical_type=unit("str"),
                ),
            ),
            # Inherited slots are binding obligations too: ``summary`` comes from the
            # ``documented`` category and ``source_version`` from the mixed-in
            # template, and the framework checks a record against the target's
            # *effective* properties.
            PropertyBinding(
                name="summary",
                expression=OperationExpression(
                    operator="coalesce",
                    arguments=(
                        _field_ref("sites", ("site_name",), unit("str", nullable=True)),
                        LiteralExpression(value="Unnamed site", logical_type=unit("str")),
                    ),
                    logical_type=unit("str"),
                ),
            ),
            PropertyBinding(
                name="source_version",
                expression=LiteralExpression(value="registry-2026-08", logical_type=unit("str")),
            ),
        ),
    )
    has_unit_binding = Binding(
        id="has_unit_binding",
        kind="edge",
        component="has_unit",
        build_key=_non_null(_field_ref("equipment", ("unit_ref",), unit("str", nullable=True)), site_key),
        source_build_key=_non_null(_field_ref("equipment", ("site_id",), unit("str", nullable=True)), site_key),
        target_build_key=_non_null(_field_ref("equipment", ("unit_ref",), unit("str", nullable=True)), site_key),
    )

    return ProjectDocument(
        project=Project(name="Monitored estate", package="kg_project"),
        annotation_types=(provenance,),
        structs=(premises, contact, contact_location),
        tables=(sites, equipment, readings, mechanical, temperature, vibration),
        projections=(
            Projection(
                id="site_cities",
                declaration_name="SiteCityProjection",
                name="site_cities",
                fields=(
                    ProjectionField(name="site_id", expression=_field_ref("sites", ("site_id",), unit("str", nullable=True))),
                    ProjectionField(
                        name="score",
                        expression=_field_ref("sites", ("priority_scores",), array(unit("int", nullable=True), nullable=True)),
                    ),
                ),
            ),
        ),
        components=(documented, provenanced, site, unit_node, monitored, has_unit),
        bindings=(site_binding, has_unit_binding),
        sources=(
            Source(id="sites_source", table="sites", location="data/sites.json", format="json", version="registry-2026-08"),
            Source(id="equipment_source", table="equipment", location="data/equipment.json", format="json"),
            Source(
                id="readings_source",
                table="readings",
                location="data",
                format="json",
                layout="{group_path}/{table_name}.json",
            ),
        ),
        modules=(
            Module(id="collapse_exact_duplicates"),
            Module(id="file", configuration={"relative_path": "graph.jsonl"}),
            Module(id="meta_graph"),
        ),
        views={"topology": {"component:site": Point(x=120.0, y=80.0).model_dump()}},  # type: ignore[arg-type]
    )


def _property(name: str, value: object, optional: bool = False) -> Property:
    return Property(name=name, logical_type=value, optional=optional)  # type: ignore[arg-type]


def test_whole_project_round_trips_through_json(document: ProjectDocument) -> None:
    restored = ProjectDocument.model_validate_json(document.model_dump_json())
    assert restored == document
    assert restored.components_by_id["has_unit"].source == "site"
    assert restored.tables_by_id["readings"].is_group


def test_framework_codecs_accept_the_embedded_ir(document: ProjectDocument) -> None:
    """The document's types and expressions are framework IR, not a dialect."""
    from kg_build_system.expressions.ir_codec import decode_expression_ir
    from kg_build_system.types.ir_codec import decode_type_ir

    for table in document.tables:
        for field in table.fields:
            decode_type_ir(field.logical_type.model_dump(mode="json"))
    for struct in document.structs:
        for field in struct.fields:
            decode_type_ir(field.logical_type.model_dump(mode="json"))
    for binding in document.bindings:
        decode_expression_ir(binding.build_key.model_dump(mode="json"))
        for property_binding in binding.properties:
            decode_expression_ir(property_binding.expression.model_dump(mode="json"))


def test_nested_struct_reference_and_array_item_types_survive(document: ProjectDocument) -> None:
    from studio_backend.ir.document import NullableType, UnitType

    sites = document.tables_by_id["sites"]
    premises = unwrap(sites.fields[2].logical_type)
    assert isinstance(premises, StructType)
    assert premises.qualname == "PremisesStruct"

    scores = unwrap(sites.fields[3].logical_type)
    assert isinstance(scores, ArrayType)
    assert isinstance(scores.item, NullableType)
    assert isinstance(scores.item.value, UnitType)
    assert scores.item.value.name == "int"
    assert isinstance(sites.fields[3].logical_type, NullableType)


def test_references_address_every_editable_part(document: ProjectDocument) -> None:
    assert refs.resolve(document, "component:site") is document.components_by_id["site"]
    assert str(refs.parse("component:site.property.summary").entity) == "component:site"
    assert refs.resolve(document, "binding:site_binding.property.name") is not None
    assert refs.resolve(document, "table:nope") is None
    with pytest.raises(refs.ReferenceError):
        refs.parse("component-site")


def test_edge_binding_requires_endpoint_keys(document: ProjectDocument) -> None:
    with pytest.raises(Exception, match="source_build_key"):
        Binding(id="broken", kind="edge", component="has_unit", build_key=document.bindings[0].build_key)


def test_concrete_component_requires_a_category_parent(document: ProjectDocument) -> None:
    with pytest.raises(Exception, match="category parent"):
        Component(id="orphan", kind="node", tier="concrete", declaration_name="OrphanNode", name="orphan")
