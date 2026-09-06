"""The authoring index: what the editor is allowed to offer, and in which order.

Tests are written against the payload the API serves (``model_dump(mode="json")``),
because the contract in ``studio/docs/API.md`` is about that JSON, and against the
framework's own effective-slot order, because ``resolved_properties`` is only useful if
it matches the class the generator will emit.
"""

from __future__ import annotations

import json
from typing import Any, cast

from authoring_support import estate, probe_topology  # noqa: F401  (pytest fixtures)
from studio_backend.ir.document import (
    Binding,
    Component,
    DataField,
    FieldExpression,
    LiteralExpression,
    OperationExpression,
    ProjectDocument,
    Projection,
    ProjectionField,
    Property,
    PropertyBinding,
    Struct,
    StructType,
    Table,
    nullable,
    unit,
)
from studio_backend.ir.index import (
    AuthoringIndex,
    ComponentEntry,
    EndpointIsCategory,
    OperatorEntry,
    ResolvedProperty,
    Selectable,
    binding_targets_without_bindings,
    build_index,
    declared_endpoints,
    endpoint_is_category,
    lineage,
    property_slot,
    resolved_properties,
    unbound_required_slots,
)

SITES_PACKAGE = "kg_project.table.sites"


def payload(index: AuthoringIndex) -> dict[str, Any]:
    return cast(dict[str, Any], index.model_dump(mode="json"))


def named(index: AuthoringIndex, kind: str, id: str) -> Selectable:
    return next(item for item in index.selectable if item.kind == kind and item.id == id)


# ------------------------------------------------------------- selectable sources


def test_every_concrete_table_and_projection_is_selectable(estate: ProjectDocument) -> None:
    """Tables first, then projections, each in the document's own order."""
    index = build_index(estate)
    assert [(item.kind, item.id) for item in index.selectable] == [
        ("table", "sites"),
        ("table", "equipment"),
        ("table", "temperature_readings"),
        ("table", "vibration_readings"),
        ("projection", "site_cities"),
    ]


def test_a_group_is_addressed_but_never_offered_as_a_source(estate: ProjectDocument) -> None:
    """A group compiles to its members; only the members carry fields."""
    index = build_index(estate)
    ids = {item.id for item in index.selectable}
    assert "readings" not in ids and "mechanical_readings" not in ids
    assert {"temperature_readings", "vibration_readings"} <= ids


def test_a_group_member_carries_its_bare_source_and_its_qualified_address(
    estate: ProjectDocument,
) -> None:
    """``name`` is what the IR stores; ``address`` is how the studio names it."""
    member = named(build_index(estate), "table", "vibration_readings")
    assert member.name == "vibration"
    assert member.group == "readings.mechanical"
    assert member.address == "readings.mechanical.vibration"
    assert member.declaration_name == "VibrationTable"
    assert member.ref == "table:vibration_readings"
    temperature = named(build_index(estate), "table", "temperature_readings")
    assert temperature.group == "readings"


def test_a_top_level_table_has_no_group(estate: ProjectDocument) -> None:
    sites = named(build_index(estate), "table", "sites")
    assert sites.group is None and sites.address == "sites" and sites.name == "sites"


def test_nested_struct_members_are_flattened_with_nullability(estate: ProjectDocument) -> None:
    """The deep path in the API example, with the nullable parent's rule applied."""
    sites = named(build_index(estate), "table", "sites")
    paths = {item.path: item for item in sites.paths}
    assert ("site_id",) in paths and paths[("site_id",)].nullable is True
    deep = paths[("premises", "contact", "location", "city")]
    assert deep.nullable is True
    assert deep.logical_type == nullable(unit("str"))
    # A non-null member reached through a nullable record becomes nullable too.
    registered = paths[("premises", "registered")]
    assert registered.logical_type == nullable(unit("date"))


def test_flattening_is_depth_first_and_lists_are_leaves(estate: ProjectDocument) -> None:
    sites = named(build_index(estate), "table", "sites")
    assert [item.path for item in sites.paths] == [
        ("site_id",),
        ("site_name",),
        ("premises",),
        ("premises", "contact_name"),
        ("premises", "contact"),
        ("premises", "contact", "email"),
        ("premises", "contact", "location"),
        ("premises", "contact", "location", "city"),
        ("premises", "contact", "location", "room"),
        ("premises", "registered"),
        ("priority_scores",),
        ("capacity",),
        ("score",),
        ("active",),
    ]


def test_a_list_is_not_walked_into(estate: ProjectDocument) -> None:
    """No field path names a list's item, so the index offers none either."""
    assert all(
        len(item.path) == 1 or item.path[0] != "priority_scores"
        for item in named(build_index(estate), "table", "sites").paths
    )


def test_a_projection_output_is_typed_by_its_expression(estate: ProjectDocument) -> None:
    """The document says the output is nullable; the implementation says otherwise."""
    projection = named(build_index(estate), "projection", "site_cities")
    types = {item.path[0]: item.logical_type for item in projection.paths}
    assert types["site_id"] == nullable(unit("str"))
    assert types["present_id"] == unit("str")


def test_an_empty_projection_is_not_offered(estate: ProjectDocument) -> None:
    empty = Projection(
        id="nothing",
        declaration_name="NothingProjection",
        name="nothing",
        fields=(
            ProjectionField(
                name="one", expression=column_of("sites", "postcode")  # cannot be typed
            ),
        ),
    )
    document = estate.replaced("projections", empty)
    assert "nothing" not in {item.id for item in build_index(document).selectable}


def column_of(source: str, *path: str) -> FieldExpression:
    return FieldExpression(source=source, path=path, logical_type=unit("bool"))


def test_an_ambiguous_source_name_is_offered_by_nobody(estate: ProjectDocument) -> None:
    """``compile/validation.py``: logical source names must be unique."""
    twin = estate.tables_by_id["equipment"].updated(id="equipment_copy")
    document = estate.replaced("tables", twin)
    ids = {item.id for item in build_index(document).selectable}
    assert "equipment" not in ids and "sites" in ids


def test_a_projection_sharing_a_tables_name_leaves_both_out(estate: ProjectDocument) -> None:
    clash = Projection(
        id="sites_projection",
        declaration_name="SitesProjection",
        name="equipment",
        fields=(ProjectionField(name="one", expression=column_of("sites", "site_id")),),
    )
    document = estate.replaced("projections", clash)
    ids = {item.id for item in build_index(document).selectable}
    assert "sites_projection" not in ids and "equipment" not in ids


def test_a_recursive_struct_does_not_loop_the_index() -> None:
    leaf = Struct(
        id="node",
        declaration_name="NodeStruct",
        name="node",
        fields=(
            DataField(name="label", logical_type=unit("str")),
            DataField(
                name="parent",
                logical_type=nullable(StructType(module="probe", qualname="NodeStruct")),
            ),
        ),
    )
    table = Table(
        id="tree",
        declaration_name="TreeTable",
        name="tree",
        fields=(DataField(name="root", logical_type=StructType(module="probe", qualname="NodeStruct")),),
    )
    paths = named(build_index(ProjectDocument(structs=(leaf,), tables=(table,))), "table", "tree").paths
    assert [item.path for item in paths] == [("root",), ("root", "label"), ("root", "parent")]


def test_an_unresolvable_struct_is_a_leaf_but_still_selectable() -> None:
    table = Table(
        id="t",
        declaration_name="TTable",
        name="t",
        fields=(DataField(name="ghost", logical_type=StructType(module="m", qualname="Ghost")),),
    )
    paths = named(build_index(ProjectDocument(tables=(table,))), "table", "t").paths
    assert [item.path for item in paths] == [("ghost",)]


# ---------------------------------------------------------------- component slots


def test_resolved_properties_follow_the_generated_records_order(estate: ProjectDocument) -> None:
    """Own slots first, then category, then mixin — the reference project's order."""
    site = estate.components_by_id["site"]
    slots = resolved_properties(estate, site)
    assert [item.name for item in slots] == ["name", "city", "summary", "source_version"]
    assert [item.declared_by for item in slots] == ["site", "site", "documented", "provenanced_node"]


def test_the_lineage_matches_a_python_mro(estate: ProjectDocument) -> None:
    """Bases are ``(*mixins, parent)``, so the parent is the further ancestor."""
    assert [item.id for item in lineage(estate, estate.components_by_id["site"])] == [
        "site",
        "provenanced_node",
        "documented",
    ]


def test_the_inheritance_order_is_the_frameworks_own(probe_topology: Any) -> None:
    """Same declarations, two routes: compare the index against ``cls.__mro__``.

    ``authoring_support.TOPOLOGY_SOURCE`` declares these components through the real
    authoring API, so the expected order is not this suite's reading of
    ``topology/models.py``. The framework answers twice: ``properties_for`` composes the
    slots by walking ``reversed(cls.__mro__)``, and the generated dataclass then moves
    the leaf's own slots in front. Both steps are checked, against the lineage and
    against ``dataclasses.fields`` respectively.
    """
    for declaration, mixins in (
        ("PairNode", ("first", "second")),
        ("LeafNode", ("left", "right")),
    ):
        document, leaf_id, class_names = _mirror(probe_topology, declaration, mixins)
        leaf = document.components_by_id[leaf_id]
        ancestors = list(lineage(document, leaf))
        assert [item.id for item in ancestors] == [
            class_names[item.__name__]
            for item in probe_topology.__dict__[declaration].__mro__
            if item.__name__ in class_names
        ], declaration
        composed = [
            slot.name
            for component in reversed(ancestors)
            for slot in component.properties
        ]
        assert composed == probe_topology.composition_order(
            probe_topology.__dict__[declaration]
        ), declaration
        assert [item.name for item in resolved_properties(document, leaf)] == (
            probe_topology.attribute_order(probe_topology.__dict__[declaration])
        ), declaration


def _mirror(
    module: Any, declaration: str, mixins: tuple[str, ...]
) -> tuple[ProjectDocument, str, dict[str, str]]:
    """The Studio document for one probed component, and its class-name mapping."""
    classes = {
        "FirstTemplate": "first",
        "SecondTemplate": "second",
        "SharedTemplate": "shared",
        "LeftTemplate": "left",
        "RightTemplate": "right",
        "BaseAbstractNode": "base",
    }
    templates = {
        "first": _template("first", "alpha", declaration="FirstTemplate"),
        "second": _template("second", "beta", declaration="SecondTemplate"),
        "shared": _template("shared", "stamp", declaration="SharedTemplate"),
        "left": _template("left", "left_slot", mixins=("shared",), declaration="LeftTemplate"),
        "right": _template("right", "right_slot", mixins=("shared",), declaration="RightTemplate"),
    }
    leaf = Component(
        id=declaration.removesuffix("Node").lower(),
        kind="node",
        tier="concrete",
        declaration_name=declaration,
        name=declaration.removesuffix("Node").lower(),
        parent="base",
        mixins=mixins,
        properties=(_property_slot("own", unit("str")),),
    )
    classes[declaration] = leaf.id
    document = _components(
        *[templates[name] for name in mixins],
        templates["shared"],
        _category("base", "shared_slot"),
        leaf,
    )
    return document, leaf.id, classes


def test_two_mixins_compose_in_reverse_declaration_order() -> None:
    """Bases are ``(*mixins, parent)``, so the last mixin sits furthest from ``object``.

    ``reversed(cls.__mro__)`` therefore contributes parent, then the mixins back to
    front, then the class — and the class's own slots still lead the record.
    """
    first = _template("first", "alpha")
    second = _template("second", "beta")
    category = _category("base", "shared_slot")
    concrete = Component(
        id="leaf",
        kind="node",
        tier="concrete",
        declaration_name="LeafNode",
        name="leaf",
        parent="base",
        mixins=("first", "second"),
        properties=(_property_slot("own", unit("str")),),
    )
    document = _components(first, second, category, concrete)
    assert [item.id for item in lineage(document, concrete)] == [
        "leaf",
        "first",
        "second",
        "base",
    ]
    assert [item.name for item in resolved_properties(document, concrete)] == [
        "own",
        "shared_slot",
        "beta",
        "alpha",
    ]


def test_a_template_reached_twice_declares_its_slot_once() -> None:
    """A diamond: C3 places the shared template once, and it is not counted twice."""
    shared = _template("shared", "stamp")
    left = _template("left", "left_slot", mixins=("shared",))
    right = _template("right", "right_slot", mixins=("shared",))
    category = _category("base", "shared_slot")
    concrete = Component(
        id="leaf",
        kind="node",
        tier="concrete",
        declaration_name="LeafNode",
        name="leaf",
        parent="base",
        mixins=("left", "right"),
        properties=(_property_slot("own", unit("str")),),
    )
    document = _components(shared, left, right, category, concrete)
    order = [item.id for item in lineage(document, concrete)]
    assert order.count("shared") == 1
    assert order == ["leaf", "left", "right", "shared", "base"]
    assert [item.name for item in resolved_properties(document, concrete)] == [
        "own",
        "shared_slot",
        "stamp",
        "right_slot",
        "left_slot",
    ]


def _property_slot(name: str, value: Any) -> Property:
    return Property(name=name, logical_type=value)


def _template(
    id: str, slot: str, *, mixins: tuple[str, ...] = (), declaration: str | None = None
) -> Component:
    return Component(
        id=id,
        kind="node",
        tier="template",
        declaration_name=declaration or f"{id.title()}Template",
        name=id,
        mixins=mixins,
        properties=(_property_slot(slot, unit("str")),),
    )


def _category(id: str, slot: str) -> Component:
    return Component(
        id=id,
        kind="node",
        tier="category",
        declaration_name=f"{id.title()}AbstractNode",
        name=id,
        label=id.title(),
        properties=(_property_slot(slot, unit("str")),),
    )


def _components(*items: Component) -> ProjectDocument:
    return ProjectDocument(components=items)


def test_a_category_offers_only_its_own_slots(estate: ProjectDocument) -> None:
    documented = estate.components_by_id["documented"]
    assert [item.name for item in resolved_properties(estate, documented)] == ["summary"]


def test_an_optional_slot_says_so(estate: ProjectDocument) -> None:
    documented = estate.components_by_id["documented"]
    documented = documented.updated(
        properties=(*documented.properties, _property("note", unit("str"), optional=True))
    )
    document = estate.replaced("components", documented)
    site = document.components_by_id["site"]
    slots = {item.name: item for item in resolved_properties(document, site)}
    assert slots["note"].optional is True
    assert slots["note"].declared_by == "documented"
    assert slots["name"].optional is False


def test_a_redeclared_slot_keeps_its_position_and_names_the_closer_owner(
    estate: ProjectDocument,
) -> None:
    """``properties_for`` replaces the declaration, not the position, on shadowing."""
    documented = estate.components_by_id["documented"]
    site = estate.components_by_id["site"]
    site = site.updated(properties=(*site.properties, _property("summary", unit("int"))))
    document = estate.updated(
        components=(documented, estate.components_by_id["provenanced_node"], site)
    )
    slots = {item.name: item for item in resolved_properties(document, document.components_by_id["site"])}
    assert slots["summary"].declared_by == "site"
    assert slots["summary"].logical_type == unit("int")


def _property(name: str, value: Any, optional: bool = False) -> Property:
    return Property(name=name, logical_type=value, optional=optional)


def test_property_slot_resolves_an_inherited_name(estate: ProjectDocument) -> None:
    slot = property_slot(estate, "site", "source_version")
    assert slot is not None and slot.declared_by == "provenanced_node"
    assert property_slot(estate, "site", "nope") is None
    assert property_slot(estate, "no_component", "summary") is None


def test_the_index_publishes_the_same_slots_as_the_helper(estate: ProjectDocument) -> None:
    entry = next(item for item in build_index(estate).components if item.id == "site")
    assert [item.name for item in entry.resolved_properties] == [
        item.name for item in resolved_properties(estate, estate.components_by_id["site"])
    ]


def test_json_is_the_documented_shape(estate: ProjectDocument) -> None:
    body = payload(build_index(estate))
    assert set(body) == {"selectable", "components", "operators"}
    site = next(item for item in body["components"] if item["id"] == "site")
    assert set(site) == {
        "id",
        "ref",
        "kind",
        "tier",
        "declaration_name",
        "name",
        "description",
        "resolved_properties",
        "endpoint_is_category",
    }
    assert set(site["endpoint_is_category"]) == {"source", "target"}
    assert set(site["resolved_properties"][0]) == {
        "name",
        "ref",
        "logical_type",
        "optional",
        "declared_by",
        "description",
    }
    table = next(item for item in body["selectable"] if item["id"] == "sites")
    assert set(table) == {
        "kind",
        "id",
        "ref",
        "name",
        "address",
        "declaration_name",
        "group",
        "description",
        "paths",
    }
    assert set(table["paths"][0]) == {"path", "logical_type", "nullable", "description"}


def test_the_payload_is_plain_json(estate: ProjectDocument) -> None:
    assert json.loads(json.dumps(payload(build_index(estate))))["operators"][0]["operator"]


# ------------------------------------------------------------- endpoint categories


def test_a_node_has_no_endpoint_categories(estate: ProjectDocument) -> None:
    site = next(item for item in build_index(estate).components if item.id == "site")
    assert site.endpoint_is_category == EndpointIsCategory(source=False, target=False)


def test_a_concrete_edge_with_concrete_endpoints_needs_no_tokens(estate: ProjectDocument) -> None:
    has_unit = next(item for item in build_index(estate).components if item.id == "has_unit")
    assert has_unit.endpoint_is_category.source is False
    assert has_unit.endpoint_is_category.target is False


def test_an_edge_over_categories_needs_an_endpoint_token_on_both_sides(
    estate: ProjectDocument,
) -> None:
    """``binding/factories.py`` requires ``source_node=`` exactly when the side is abstract."""
    monitored = next(
        item for item in build_index(estate).components if item.id == "monitored_relation"
    )
    assert monitored.endpoint_is_category == EndpointIsCategory(source=True, target=True)


def test_only_the_abstract_side_of_an_edge_asks_for_a_token(estate: ProjectDocument) -> None:
    documented = estate.components_by_id["documented"]
    mixed = estate.components_by_id["monitored_relation"].updated(
        id="mixed",
        declaration_name="MixedAbstractEdge",
        name="mixed",
        source="documented",
        target="documented",
    )
    child = Component(
        id="mixed_child",
        kind="edge",
        tier="concrete",
        declaration_name="MixedChildEdge",
        name="mixed_child",
        parent="mixed",
        source=documented.name,
        target="site",
    )
    document = estate.updated(
        components=(*estate.components, mixed, child),
    )
    entry = next(item for item in build_index(document).components if item.id == "mixed_child")
    assert entry.endpoint_is_category == EndpointIsCategory(source=True, target=False)


def test_endpoints_are_inherited_from_the_edge_parent(estate: ProjectDocument) -> None:
    """``_resolve_edge_endpoints`` lets a child inherit rather than restate."""
    parent = estate.components_by_id["monitored_relation"]
    child = Component(
        id="inheriting",
        kind="edge",
        tier="template",
        declaration_name="InheritingEdgeTemplate",
        name="inheriting",
        parent="monitored_relation",
    )
    document = estate.replaced("components", child)
    assert declared_endpoints(document, child) == ("documented", "documented")
    assert endpoint_is_category(document, child) == EndpointIsCategory(source=True, target=True)
    assert parent.source == "documented"


def test_a_dangling_endpoint_answers_false(estate: ProjectDocument) -> None:
    broken = estate.components_by_id["has_unit"].updated(source="nowhere", target="unit")
    document = estate.replaced("components", broken)
    entry = next(item for item in build_index(document).components if item.id == "has_unit")
    assert entry.endpoint_is_category == EndpointIsCategory(source=False, target=False)


# ----------------------------------------------------------------- the operators


def test_the_operator_array_is_the_catalogue(estate: ProjectDocument) -> None:
    from studio_backend.ir.infer import OPERATION_CATALOGUE, OPERATORS

    entries = build_index(estate).operators
    assert [item.operator for item in entries] == list(OPERATORS)
    assert len(entries) == 21
    for entry in entries:
        spec = OPERATION_CATALOGUE[entry.operator]
        assert entry.label == spec["label"]
        assert entry.group == spec["group"]
        assert entry.arity == spec["arity"]
        assert entry.render == spec["render"]
        assert entry.produces == spec["produces"]["shape"]
        assert entry.produces_type_rule == spec["produces"]["type_rule"]
        assert entry.requires == spec["requires"]


def test_an_operator_entry_carries_the_documented_keys(estate: ProjectDocument) -> None:
    body = payload(build_index(estate))["operators"]
    assert set(body[0]) == {
        "operator",
        "label",
        "requires",
        "produces",
        "produces_type_rule",
        "produces_description",
        "arity",
        "group",
        "docs",
        "render",
    }
    where = next(item for item in body if item["operator"] == "where_present")
    assert where["requires"] == {"shape": "nullable", "arguments": [], "parameters": []}
    assert where["produces"] == "non_null_unwrapped"
    assert where["arity"] == 1
    assert where["group"] == "effect"


def test_operator_entries_are_rebuilt_from_the_catalogue_each_time() -> None:
    from studio_backend.ir.index import operator_entries

    assert operator_entries() == operator_entries()
    assert all(isinstance(item, OperatorEntry) for item in operator_entries())


# ----------------------------------------------------------- binding-side helpers


def test_only_unbound_concrete_components_are_offered_as_targets(estate: ProjectDocument) -> None:
    targets = binding_targets_without_bindings(estate)
    assert [item.id for item in targets] == ["unit"]


def test_a_component_loses_its_place_as_soon_as_one_binding_exists(estate: ProjectDocument) -> None:
    binding = Binding(
        id="unit_binding",
        kind="node",
        component="unit",
        build_key=OperationExpression(  # type: ignore[call-arg]
            operator="where_present",
            arguments=(column_of("equipment", "unit_ref"),),
            logical_type=unit("str"),
        ),
    )
    document = estate.replaced("bindings", binding)
    assert "unit" not in [item.id for item in binding_targets_without_bindings(document)]


def test_a_binding_that_omits_inherited_slots_owes_them(estate: ProjectDocument) -> None:
    """Inherited slots are obligations, so dropping them from a record is a gap."""
    binding = estate.bindings_by_id["site_binding"]
    stripped = binding.updated(
        properties=[
            item for item in binding.properties if item.name not in {"summary", "source_version"}
        ]
    )
    document = estate.replaced("bindings", stripped)
    missing = unbound_required_slots(document, stripped)
    assert [item.name for item in missing] == ["summary", "source_version"]
    assert [item.declared_by for item in missing] == ["documented", "provenanced_node"]


def test_a_binding_that_fills_inherited_slots_owes_nothing(estate: ProjectDocument) -> None:
    """The reference-shaped binding covers the slots it inherits."""
    assert [item.name for item in unbound_required_slots(estate, estate.bindings_by_id["site_binding"])] == []


def test_a_binding_that_covers_everything_owes_nothing(estate: ProjectDocument) -> None:
    binding = estate.bindings_by_id["site_binding"]
    site = estate.components_by_id["site"]
    filled = tuple(
        PropertyBinding(
            name=slot.name,
            expression=OperationExpression(  # type: ignore[call-arg]
                operator="coalesce",
                arguments=(
                    column_of("sites", "site_name"),
                    LiteralExpression(value="x", logical_type=unit("str")),
                ),
                logical_type=slot.logical_type,
            ),
        )
        for slot in resolved_properties(estate, site)
        if slot.name in {"name", "city", "summary", "source_version"}
    )
    complete = binding.updated(properties=filled)
    assert unbound_required_slots(estate, complete) == ()


def test_an_optional_slot_is_not_required(estate: ProjectDocument) -> None:
    documented = estate.components_by_id["documented"]
    documented = documented.updated(
        properties=(*documented.properties, _property("note", nullable(unit("str")), optional=True))
    )
    document = estate.replaced("components", documented)
    binding = document.bindings_by_id["site_binding"]
    assert "note" not in [item.name for item in unbound_required_slots(document, binding)]


def test_a_binding_of_an_unknown_component_reports_nothing_rather_than_guessing(
    estate: ProjectDocument,
) -> None:
    orphan = Binding(
        id="orphan",
        kind="node",
        component="nope",
        build_key=OperationExpression(  # type: ignore[call-arg]
            operator="where_present",
            arguments=(column_of("sites", "site_id"),),
            logical_type=unit("str"),
        ),
    )
    assert unbound_required_slots(estate, orphan) == ()


# --------------------------------------------------------------------- stability


def test_one_document_always_builds_the_same_index(estate: ProjectDocument) -> None:
    """Deterministic by construction: no set or scratch dict is ever iterated for output."""
    assert payload(build_index(estate)) == payload(build_index(estate))


def test_reordering_the_document_reorders_the_index_but_not_its_content(
    estate: ProjectDocument,
) -> None:
    """The index follows the document, and only the document."""
    flipped = estate.updated(components=tuple(reversed(estate.components)))
    forward = payload(build_index(estate))
    backward = payload(build_index(flipped))
    assert [item["id"] for item in forward["components"]] == [
        item["id"] for item in reversed(backward["components"])
    ]
    assert {json.dumps(item, sort_keys=True) for item in forward["components"]} == {
        json.dumps(item, sort_keys=True) for item in backward["components"]
    }


def test_an_empty_document_still_builds(estate: ProjectDocument) -> None:
    index = build_index(ProjectDocument())
    assert index.selectable == () and index.components == ()
    assert len(index.operators) == 21


def test_the_index_is_readable_as_the_models_it_claims_to_be(estate: ProjectDocument) -> None:
    index = build_index(estate)
    assert isinstance(index, AuthoringIndex)
    assert all(isinstance(item, Selectable) for item in index.selectable)
    assert all(isinstance(item, ComponentEntry) for item in index.components)
    site = next(item for item in index.components if item.id == "site")
    assert all(isinstance(item, ResolvedProperty) for item in site.resolved_properties)
    assert isinstance(site.endpoint_is_category, EndpointIsCategory)


def test_the_array_item_of_a_list_path_keeps_its_own_nullability(estate: ProjectDocument) -> None:
    path = named(build_index(estate), "table", "sites").paths
    scores = next(item for item in path if item.path == ("priority_scores",))
    assert scores.nullable is True
    assert scores.logical_type.kind == "nullable"
    inner = scores.logical_type.value
    assert inner.kind == "array" and inner.item.kind == "nullable"
